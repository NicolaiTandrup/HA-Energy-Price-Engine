"""Read-only operational views of the authoritative ledger; never fetch or compose."""

import json
from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .api import ConsumerAPI
from .price_engine import day_bounds


def interval_result(coordinator, start, end, now):
    return ConsumerAPI(coordinator.hass).lookup(
        coordinator.site["id"],
        start,
        end,
        now=now,
        producer_entry_id=coordinator.entry.entry_id,
    )


def day_result(coordinator, offset=0, now=None):
    now = now or dt_util.utcnow()
    site = coordinator.site
    day = now.astimezone(ZoneInfo(site["timezone"])).date() + timedelta(days=offset)
    return interval_result(coordinator, *day_bounds(day, site["timezone"]), now)


def source_status(coordinator, now=None):
    now = now or dt_util.utcnow()
    site = coordinator.site
    result = day_result(coordinator, now=now)
    source = coordinator.hass.config_entries.async_get_entry(site.get("nordpool_entry", ""))
    reports = coordinator.schedule.days.get(site["id"], {})
    today = str(now.astimezone(ZoneInfo(site["timezone"])).date())
    report = reports.get(today, {})
    return {
        "requested_date": today,
        "site_id": site["id"],
        "site_name": site["name"],
        "source": source.title if source else site.get("price_entity", "Source unavailable"),
        "area": site["area"],
        "currency": "DKK",
        "resolution_minutes": 15,
        "health": str(result.status),
        "last_success": result.last_success,
        "last_attempt": report.get("last_attempt"),
        "last_error": result.reason,
        "required_action": report.get("required_action"),
        "missing_components": report.get("missing_components", []),
        "affected_period": report.get("affected_period"),
        "valid_slots": result.valid_slots,
        "expected_slots": result.expected_slots,
        "next_scheduled_update": coordinator.schedule.next_update(now).isoformat(),
        "dso_mode": site.get("dso_mode", "manual"),
    }


def slot_breakdown(coordinator, start, now=None):
    """Explain one stored UTC quarter, retaining degraded status and original revision."""
    now = now or dt_util.utcnow()
    result = interval_result(coordinator, start, start + timedelta(minutes=15), now)
    if not result.records:
        return f"{start.isoformat()}: {result.status}. No stored price. Missing is not zero."
    row = result.records[0]
    payload = json.loads(row.components_json)
    source = json.loads(row.source_json)
    display_unit = coordinator.site.get("display_unit", "øre/kWh")
    factor = 100 if display_unit == "øre/kWh" else 1
    lines = [
        f"{row.start.isoformat()} – {row.end.isoformat()} (UTC)",
        f"Status: {result.status}; revision: {row.revision}; verified: {result.last_success or 'unverified'}",
        f"Preferred display: {row.final_price_incl_vat * factor:.6f} {display_unit} including VAT",
        f"Stored final: {row.final_price_incl_vat:.6f} DKK/kWh including VAT (unchanged API unit)",
    ]
    lines.append(
        f"Stored source: {source.get('kind', 'recorded provider')}; "
        f"input unit: {source.get('input_unit', 'provider contract')}; "
        f"input VAT: {source.get('input_vat', 'provider contract')}; "
        f"original verification: {source.get('verified_at', 'see diagnostics')}"
    )
    if source.get("dso"):
        dso = source["dso"]
        lines.append(
            f"Grid source: {dso.get('provider')}; product: {dso.get('product')}; "
            f"verified: {dso.get('fetched_at')}; effective ranges: {dso.get('effective_ranges')}"
        )
    for name, part in payload.get("components", {}).items():
        lines.append(
            f"{name}: {part['ex_vat'] * factor:.6f} ex VAT + {part['vat'] * factor:.6f} VAT = "
            f"{part['incl_vat'] * factor:.6f} {display_unit}; verified {part.get('verified_on', 'see source')}; "
            f"period {part.get('valid_from', 'source interval')} – {part.get('valid_to', 'source interval')}; "
            f"locked {part.get('locked', False)}; source: {part.get('source', 'see input/grid source')}"
        )
    if "external_all_in" in payload:
        lines.append("Provider final all-in price; no additional tariff or VAT applied.")
    if payload.get("fixed_subscriptions_excluded"):
        lines.append("Fixed subscriptions excluded from this marginal price (DKK/month):")
        for part in payload["fixed_subscriptions_excluded"]:
            lines.append(f"{part['id']}: {part['incl_vat']:.6f} including VAT")
    if result.reason:
        lines.append(f"Verification issue: {result.reason}")
    return "\n".join(lines)
