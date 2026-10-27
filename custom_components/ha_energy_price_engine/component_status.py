"""Concrete applied component values and native corrective routes per saved site."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .api import ConsumerAPI
from .configuration import settings, tariff_for
from .const import DOMAIN
from .localization import review_labels
from .models import PriceSlot
from .price_components import normalize_component, resolved_rules

COMPONENT_STEPS = {
    "source": "setup_spot",
    "dso": "setup_dso",
    "supplier": "setup_supplier",
    "energinet_net": "setup_net",
    "energinet_system": "setup_system",
    "electricity_tax": "setup_electricity_tax",
    "vat": "setup_vat",
    "final": "setup_final",
}


def safe(value):
    return (
        str(value)
        .replace("|", "/")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("[", "")
        .replace("]", "")[:160]
    )


def component_snapshot(hass, entry):
    site = settings(entry)
    now = dt_util.utcnow()
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    reference = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
    activation = dt_util.parse_datetime(site.get("pricing_start", ""))
    if activation:
        reference = max(reference, activation)
    day = str(reference.astimezone(ZoneInfo(site["timezone"])).date())
    if runtime and not getattr(runtime, "settings_current", True):
        runtime = None
    inputs = runtime.price_updater.component_inputs.get(day, {}) if runtime else {}
    tariff = inputs.get("tariff", tariff_for(site))
    source = inputs.get("source", {})
    raw = runtime.price_updater.raw_reports.get(day, {}) if runtime else {}
    stamp = dt_util.parse_datetime(raw.get("verified_at", ""))
    fresh = bool(stamp and 0 <= (now - stamp).total_seconds() < 7200)
    spot = (
        next(
            (
                r
                for r in runtime.price_updater.raw_slots.get(day, ())
                if r.start <= reference < r.end
            ),
            None,
        )
        if runtime
        else None
    )
    parts, _ = (
        resolved_rules(spot or PriceSlot(reference, reference + timedelta(minutes=15), 0), tariff)
        if tariff.get("mode") != "all_in"
        else ({}, [])
    )
    result = {}

    def add(key, value=None, source_key="", status="missing", period="", **more):
        result[key] = {
            "component": key,
            "value": value,
            "unit": "%"
            if key == "vat"
            else "øre/kWh ex VAT"
            if key != "final"
            else "øre/kWh incl VAT",
            "source": source_key,
            "display_value": more.pop("display_value", value),
            "status": status,
            "effective_period": period,
            "action": COMPONENT_STEPS[key],
            **more,
        }

    add(
        "source",
        spot.price * 100 if spot else None,
        "Nord Pool" if site.get("source_type") == "nordpool" else "provider",
        "verified" if spot and fresh and raw.get("status") == "READY" else "unavailable",
    )
    if spot:
        result["source"]["display_value"] = (
            spot.price
            * 100
            * (1 if site.get("price_basis") in {"spot_incl_vat", "all_in"} else 1 + site["vat"])
        )
    for key in ("dso", "supplier", "energinet_net", "energinet_system", "electricity_tax"):
        if site.get("price_basis") == "all_in":
            add(key, source_key="provider_included", status="included")
            continue
        part = parts.get(key)
        if part:
            add(
                key,
                part["ex_vat"] * 100,
                part["source"],
                "verified",
                part["valid_from"] + " → " + part["valid_to"],
                display_value=part["incl_vat"] * 100,
            )
        elif key == "dso" and inputs:
            grid = [
                s
                for s in tariff.get("grid_slots", [])
                if s.start <= reference and s.end >= reference + timedelta(minutes=15)
            ]
            if len(grid) == 1:
                warning = source.get("dso", {}).get("warning")
                add(
                    key,
                    grid[0].price * 100,
                    source.get("dso", {}).get("provider", "Radius"),
                    "unavailable" if warning else "verified",
                    day,
                    display_value=grid[0].price * 100 * (1 + site["vat"]),
                )
                continue
            add(key)
        elif key == "supplier" and (provisional := site.get("provisional_supplier")):
            normalized = normalize_component(
                {
                    **provisional,
                    "id": "supplier",
                    "verified_on": provisional["approved_on"],
                    "source": "user_approved_provisional_NOT_verified",
                }
            )
            valid = provisional["valid_from"] <= day < provisional["valid_to"]
            add(
                key,
                normalized["ex_vat"] * 100,
                "provisional_contract",
                "provisional" if valid else "expired",
                provisional["valid_from"] + " → " + provisional["valid_to"],
                display_value=normalized["incl_vat"] * 100,
            )
        else:
            add(key)
    add("vat", site["vat"] * 100, "confirmed_vat", "verified")
    lookup = ConsumerAPI(hass).lookup(site["id"], reference, reference + timedelta(minutes=15))
    final = (
        lookup.records[0].final_price_incl_vat * 100
        if lookup.records and str(lookup.status) == "READY"
        else None
    )
    estimated = (
        next(
            (r for r in runtime.price_updater.estimated_slots.get(day, ()) if r.start == reference),
            None,
        )
        if runtime
        else None
    )
    add(
        "final",
        final if final is not None else estimated.price * 100 if estimated else None,
        "calculated",
        "verified" if final is not None else "provisional" if estimated else "missing",
        reference.isoformat(),
    )
    return {
        "components": result,
        "reference": reference.isoformat(),
        "scope_start": site.get("pricing_start"),
        "api_status": str(lookup.status),
        "raw_status": raw.get("status", "INCOMPLETE"),
        "monthly_subscription": [
            r
            for r in site.get("dated_components", [])
            if r["id"] == "supplier_subscription" and r["valid_from"] <= day < r["valid_to"]
        ],
        "coverage": runtime.schedule.days.get(site["id"], {}) if runtime else {},
    }


async def review(hass, entry, details=False, only=None):
    labels = await review_labels(hass)
    data = component_snapshot(hass, entry)

    def t(key):
        return labels.get(key, key)

    menu = {}
    lines = []
    missing = []
    site = settings(entry)
    for key, row in data["components"].items():
        if only and key not in only:
            continue
        value = (
            "—"
            if row["display_value"] is None
            else f"{row['display_value']:.3f}".rstrip("0").rstrip(".")
        )
        value = value.replace(".", t("decimal_separator"))
        unit = "%" if key == "vat" else "øre"
        if key == "source":
            name = "Nord Pool" if site.get("source_type") == "nordpool" else t("provider_source")
        else:
            name = labels.get("compact_" + key, t(key))
        status = t(row["status"])
        mark = (
            "✓" if row["status"] == "verified" else "~" if row["status"] == "provisional" else "!"
        )
        source = row["source"]
        source_label = (
            "EWII"
            if "ewii.dk" in source
            else "Radius"
            if key == "dso" and site.get("dso_mode") == "radius_c"
            else t("own_source")
            if key in {"supplier", "dso"}
            else ""
        )
        menu[row["action"]] = f"{mark} {name} · {value} {unit} · {status}" + (
            f" · {source_label}" if source_label else ""
        )
        source_text = source
        if source.startswith("user_") or source == "provisional_contract":
            source_text = t("own_source_details")
        elif source.startswith("Rate specified by owner"):
            source_text = t("public_baseline")
        elif source == "calculated":
            source_text = "Energy Price Engine"
        elif source == "confirmed_vat":
            source_text = t("confirmed_vat_label")
        action = t("edit_" + key)
        period = safe(row["effective_period"]).replace("9999-12-31", t("until_changed"))
        lines.append(
            f"**{safe(name)}**: {value} {t('unit_incl_vat') if key != 'vat' else '%'} · {safe(status)}\n\n{safe(source_text) or '—'} · {period or '—'}\n\n{safe(t('fix_' + key)) if row['status'] != 'verified' else safe(action)}"
        )
        if row["status"] not in {"verified"}:
            target = {
                "source": "setup_site",
                "dso": "setup_grid",
                "supplier": "setup_supplier",
                "energinet_net": "setup_tax_details",
                "energinet_system": "setup_tax_details",
                "electricity_tax": "setup_tax_details",
            }.get(key)
            if target:
                missing.append(target)
    for monthly in data["monthly_subscription"] if only is None else []:
        normalized = normalize_component(monthly)
        lines.append(
            f"**{t('monthly_label')}**: {normalized['incl_vat']:g} {t('monthly_unit')} · {t('subscription_excluded')}"
        )
    coverage = []
    today = dt_util.utcnow().astimezone(ZoneInfo(site["timezone"])).date()
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    for offset in (0, 1):
        day = str(today + timedelta(days=offset))
        report = data["coverage"].get(day, {})
        raw = runtime.price_updater.raw_reports.get(day, {}) if runtime else {}
        coverage.append(
            f"{t('today' if offset == 0 else 'tomorrow')} {day}: {t('raw_label')} {raw.get('valid_slots', 0)}/{raw.get('expected_slots', 0)} · {t('final_label')} {report.get('valid_slots', 0)}/{report.get('expected_slots', 0)}"
        )
    return {
        "name": safe(site["name"]),
        "coverage": " · ".join(coverage) or "—",
        "components": "\n\n---\n\n".join(lines),
        "rows": menu,
        "start": (
            t("starts_at")
            + " "
            + dt_util.parse_datetime(data["scope_start"])
            .astimezone(ZoneInfo(site["timezone"]))
            .strftime("%H:%M")
        )
        if data.get("scope_start")
        and dt_util.parse_datetime(data["scope_start"]) > dt_util.utcnow()
        else "",
    }, missing
