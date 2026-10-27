"""Read-only operational views of the authoritative ledger; never fetch or compose."""

import json
from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .api import ConsumerAPI
from .configuration import settings
from .presentation import format_price
from .price_engine import day_bounds


def interval_result(coordinator, start, end, now):
    return ConsumerAPI(coordinator.hass).lookup(
        coordinator.site["id"],
        start,
        end,
        now=now,
        producer_entry_id=coordinator.entry.entry_id,
    )


def quarter_result(coordinator, offset=0, now=None):
    now = now or dt_util.utcnow()
    start = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0) + timedelta(
        minutes=15 * offset
    )
    return interval_result(coordinator, start, start + timedelta(minutes=15), now)


def readiness_snapshot(hass, entry, *, start=None, end=None, now=None):
    now = now or dt_util.utcnow()
    site = settings(entry)
    current = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
    day = now.astimezone(ZoneInfo(site["timezone"])).date()
    ranges = {
        "current": (current, current + timedelta(minutes=15)),
        "next": (current + timedelta(minutes=15), current + timedelta(minutes=30)),
        "history_today": day_bounds(day, site["timezone"]),
        "history_tomorrow": day_bounds(day + timedelta(days=1), site["timezone"]),
    }
    if start is not None or end is not None:
        if start is None or end is None:
            raise ValueError("Both requested horizon boundaries are required")
        ranges["requested"] = (start, end)
    api = ConsumerAPI(hass)
    facts = {}
    for key, (first, last) in ranges.items():
        result = api.lookup(site["id"], first, last, now=now, producer_entry_id=entry.entry_id)
        facts[key] = {
            "start": first.isoformat(),
            "end": last.isoformat(),
            "status": str(result.status),
            "valid_slots": result.valid_slots,
            "expected_slots": result.expected_slots,
            "last_success": result.last_success,
        }
    activation = dt_util.parse_datetime(site.get("pricing_start", ""))
    facts["missing_before_activation"] = bool(
        activation
        and ranges["history_today"][0] < activation < ranges["history_today"][1]
        and facts["history_today"]["status"] == "INCOMPLETE"
    )
    return facts


def day_result(coordinator, offset=0, now=None):
    now = now or dt_util.utcnow()
    site = coordinator.site
    day = now.astimezone(ZoneInfo(site["timezone"])).date() + timedelta(days=offset)
    return interval_result(coordinator, *day_bounds(day, site["timezone"]), now)


def source_status(coordinator, now=None):
    now = now or dt_util.utcnow()
    site = coordinator.site
    result = day_result(coordinator, now=now)
    current = quarter_result(coordinator, now=now)
    following = quarter_result(coordinator, 1, now)
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
        "health": str(current.status),
        "health_scope": "current_quarter",
        "current_quarter_status": str(current.status),
        "next_quarter_status": str(following.status),
        "historical_day_status": str(result.status),
        "coverage_scope": "historical_full_day",
        "last_success": result.last_success,
        "last_attempt": report.get("last_attempt"),
        "last_error": current.reason,
        "historical_coverage_reason": result.reason,
        "required_action": report.get("required_action"),
        "missing_components": report.get("missing_components", []),
        "affected_period": report.get("affected_period"),
        "valid_slots": result.valid_slots,
        "stored_slots": result.valid_slots,
        "verified_final_slots": report.get("valid_slots", 0),
        "raw_status": coordinator.price_updater.raw_reports.get(today, {}).get("status"),
        "raw_valid_slots": coordinator.price_updater.raw_reports.get(today, {}).get(
            "valid_slots", 0
        ),
        "raw_verified_at": coordinator.price_updater.raw_reports.get(today, {}).get("verified_at"),
        "expected_slots": result.expected_slots,
        "prices_start_at": site.get("pricing_start"),
        "next_scheduled_update": coordinator.schedule.next_update(now).isoformat(),
        "dso_mode": site.get("dso_mode", "manual"),
    }


def slot_breakdown(coordinator, start, now=None):
    """Canonical technical facts; native UI resources supply all explanatory prose."""
    now = now or dt_util.utcnow()
    result = interval_result(coordinator, start, start + timedelta(minutes=15), now)
    facts = {
        "start": start.isoformat(),
        "status": str(result.status),
        "records": len(result.records),
    }
    if result.records:
        row = result.records[0]
        unit = coordinator.site.get("display_unit", "øre/kWh")
        facts.update(
            end=row.end.isoformat(),
            revision=row.revision,
            final_price_incl_vat=row.final_price_incl_vat,
            canonical_unit="DKK/kWh",
            display_value=row.final_price_incl_vat * (100 if unit == "øre/kWh" else 1),
            display_unit=unit,
            display_text=format_price(row.final_price_incl_vat, unit),
            canonical_technical_values=True,
            source=json.loads(row.source_json),
            components=json.loads(row.components_json),
        )
    return "```json\n" + json.dumps(facts, indent=2, ensure_ascii=False) + "\n```"
