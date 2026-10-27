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
        "stored_slots": result.valid_slots,
        "verified_final_slots": report.get("valid_slots", 0),
        "raw_status": coordinator.price_updater.raw_reports.get(today, {}).get("status"),
        "raw_valid_slots": coordinator.price_updater.raw_reports.get(today, {}).get(
            "valid_slots", 0
        ),
        "raw_verified_at": coordinator.price_updater.raw_reports.get(today, {}).get("verified_at"),
        "expected_slots": result.expected_slots,
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
            source=json.loads(row.source_json),
            components=json.loads(row.components_json),
        )
    return "```json\n" + json.dumps(facts, indent=2, ensure_ascii=False) + "\n```"
