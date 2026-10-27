"""Human-readable current/future marginal prices from canonical resolved records."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .component_status import component_snapshot, safe
from .configuration import settings
from .const import DOMAIN
from .localization import review_labels
from .presentation import format_price


def quarter_choices(hass, entry):
    """Available raw/stored quarters, with UTC offsets distinguishing DST folds."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    now = dt_util.utcnow()
    current = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
    starts = {current}
    if runtime:
        starts.update(r.start for rows in runtime.price_updater.raw_slots.values() for r in rows)
        starts.update(
            r.start
            for r in runtime.price_engine.lookup(
                runtime.site["id"], current - timedelta(days=1), current + timedelta(days=2)
            )
        )
    zone = ZoneInfo(settings(entry)["timezone"])
    return [
        (s.isoformat(), s.astimezone(zone).isoformat(timespec="minutes")) for s in sorted(starts)
    ]


async def charging_breakdown(hass, entry, start):
    labels = await review_labels(hass)
    data = component_snapshot(hass, entry, reference=start)

    def text(key):
        return labels.get(key, key)

    unit = settings(entry).get("display_unit", "øre/kWh")

    def amount(value):
        return format_price(value, unit, text("decimal_separator"), from_ore=True)

    def price_unit(key):
        return text(key).replace("øre/kWh", unit)

    zone = ZoneInfo(settings(entry)["timezone"])
    lines = [f"**{start.astimezone(zone).isoformat(timespec='minutes')}**"]
    for key in (
        "source",
        "dso",
        "energinet_net",
        "energinet_system",
        "supplier",
        "electricity_tax",
    ):
        row = data["components"][key]
        name = "Nord Pool" if key == "source" else text(key)
        source = row["source"]
        if row["status"] == "provisional":
            source = text("provisional_source")
        elif source.startswith("user_") or source == "provisional_contract":
            source = text("own_source_details")
        elif source.startswith("Rate specified by owner"):
            source = text("public_baseline")
        period = safe(row["effective_period"]).replace("9999-12-31", text("until_changed"))
        lines.append(
            f"**{name}: {amount(row['value'])} {price_unit('unit_ex_vat')}** · {text(row['status'])}\n\n{safe(source) or '—'} · {period or '—'}"
        )
    final = data["components"]["final"]
    lines.append(
        f"**{text('vat_amount')}: {amount(data['canonical_vat_ore'])} {unit}** · {text(data['components']['vat']['status'])} · {text('confirmed_vat_label')}"
    )
    lines.append(
        f"**{text('final')}: {amount(final['display_value'])} {price_unit('unit_incl_vat')}** · {text(final['status'])}"
    )
    if data["canonical_ex_vat_ore"] is not None:
        lines.append(
            f"{amount(data['canonical_ex_vat_ore'])} + {amount(data['canonical_vat_ore'])} = {amount(final['display_value'])} {unit}"
        )
    lines.append(text("marginal_only"))
    activation = dt_util.parse_datetime(data.get("scope_start") or "")
    if activation and start < activation:
        lines.append(
            text("starts_at") + " " + activation.astimezone(zone).isoformat(timespec="minutes")
        )
    if data["reason"]:
        stage = data["failure_stage"]
        if stage == "grid":
            lines.append(text("fix_dso"))
        elif stage == "source":
            lines.append(text("fix_source"))
        elif final["status"] == "provisional":
            lines.append(text("provisional_guidance"))
        else:
            missing = [
                text("fix_" + key)
                for key, row in data["components"].items()
                if key != "final" and row["status"] in {"missing", "expired"}
            ]
            lines.extend(dict.fromkeys(missing or [text("check_guidance")]))
    if data["verified_at"]:
        stamp = dt_util.parse_datetime(data["verified_at"])
        if stamp:
            lines.append(
                text("checked_at") + " " + stamp.astimezone(zone).isoformat(timespec="minutes")
            )
    lines.insert(1, await charging_readiness(hass, entry))
    return "\n\n---\n\n".join(lines)


async def charging_readiness(hass, entry, start=None, end=None):
    """Separate range readiness from full-day history using the unchanged API v1."""
    from .status import readiness_snapshot

    labels = await review_labels(hass)
    snapshot = readiness_snapshot(hass, entry, start=start, end=end)
    zone = ZoneInfo(settings(entry)["timezone"])
    lines = []
    for key in ("current", "next", "requested", "history_today", "history_tomorrow"):
        if key not in snapshot:
            continue
        facts = snapshot[key]
        state = labels["readiness_" + facts["status"].lower()]
        lines.append(
            f"**{labels['scope_' + key]}: {state}** · {facts['valid_slots']}/{facts['expected_slots']}"
        )
        if key == "requested":
            first, last = (
                dt_util.parse_datetime(facts[k]).astimezone(zone) for k in ("start", "end")
            )
            lines.append(
                f"{first.isoformat(timespec='minutes')} → {last.isoformat(timespec='minutes')}"
            )
            if facts["status"] != "READY":
                lines.append(labels["horizon_unavailable"])
    if snapshot["missing_before_activation"]:
        lines.append(labels["activation_history"])
    return "\n\n".join(lines)


def horizon_choices(entry):
    """Calendar choices, never fabricated price slots. API v1 has no 48h limit."""
    now = dt_util.utcnow()
    current = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
    zone = ZoneInfo(settings(entry)["timezone"])
    return [
        (stamp.isoformat(), stamp.astimezone(zone).isoformat(timespec="minutes"))
        for n in range(193)
        if (stamp := current + timedelta(minutes=15 * n))
    ]
