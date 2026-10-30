"""Device presentation from verified stored records, never fetch or compose tariffs."""

import json
from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .status import day_result, quarter_result

COMPONENTS = (
    "spot",
    "dso",
    "energinet_net",
    "energinet_system",
    "supplier",
    "electricity_tax",
    "vat",
    "final",
)


def stored_breakdown(coordinator, *, now=None):
    """One coherent current/next verified quarter; unknown is never a zero rate.

    The applied VAT *amount* is the sum already recorded for each component, so
    mixed VAT bases and negative prices are preserved without applying VAT again.
    All-in provider records deliberately cannot expose unknown component amounts.
    """
    now = now or dt_util.utcnow()
    current = quarter_result(coordinator, now=now)
    following = quarter_result(coordinator, 1, now)
    result, period = (current, "current_quarter")
    if str(current.status) != "READY" and str(following.status) == "READY":
        result, period = following, "next_quarter"
    facts = {
        "period": "unavailable",
        "verification": str(result.status).lower(),
        "current_quarter_status": str(current.status),
        "next_quarter_status": str(following.status),
        "components": {key: None for key in COMPONENTS},
        "source": {},
        "component_metadata": {},
    }
    if str(result.status) != "READY" or len(result.records) != 1:
        return facts
    record = result.records[0]
    parts = json.loads(record.components_json).get("components", {})
    zone = ZoneInfo(coordinator.site["timezone"])
    values = facts["components"]
    for key in COMPONENTS[:6]:
        if key in parts:
            values[key] = parts[key]["ex_vat"] * 100
    if parts:
        values["vat"] = sum(part["vat"] for part in parts.values()) * 100
    values["final"] = record.final_price_incl_vat * 100
    facts.update(
        period=period,
        verification="verified",
        start=record.start.isoformat(),
        end=record.end.isoformat(),
        local_start=record.start.astimezone(zone).isoformat(timespec="minutes"),
        local_end=record.end.astimezone(zone).isoformat(timespec="minutes"),
        revision=record.revision,
        calculated_at=record.calculated_at.isoformat(),
        source=json.loads(record.source_json),
        component_metadata={
            key: {k: v for k, v in part.items() if k not in {"ex_vat", "incl_vat", "vat"}}
            for key, part in parts.items()
        },
    )
    return facts


def availability(coordinator, scope="current", *, now=None):
    """Explain API results without changing their status or authorizing a window."""
    now = now or dt_util.utcnow()
    site = coordinator.site
    zone = ZoneInfo(site["timezone"])
    offset = int(scope == "tomorrow")
    result = (
        day_result(coordinator, offset, now)
        if scope in {"history", "tomorrow"}
        else quarter_result(coordinator, now=now)
    )
    day = str(now.astimezone(zone).date() + timedelta(days=offset))
    report = coordinator.schedule.days.get(site["id"], {}).get(day, {})
    raw = coordinator.price_updater.raw_reports.get(day, {})
    activation = dt_util.parse_datetime(site.get("pricing_start", ""))
    start = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
    missing = report.get("missing_components", [])
    state = str(result.status)
    code = "missing_prices"
    if state == "READY":
        code = "ready"
    elif (
        site["id"] in coordinator.price_engine.load_errors
        or report.get("failure_stage") == "storage"
    ):
        code = "storage_error"
    elif missing or report.get("failure_stage") == "configuration":
        code = "missing_components"
    elif state == "ERROR":
        code = "verification_error"
    elif state == "STALE":
        code = "stale"
    elif (
        scope == "current"
        and activation
        and start < activation <= start + timedelta(minutes=15)
        and now < activation
        and str(quarter_result(coordinator, 1, now).status) == "READY"
    ):
        code = "waiting_first_quarter"
    elif not report and not raw:
        code = "loading"
    elif scope == "tomorrow" and not raw.get("valid_slots") and raw.get("status") == "INCOMPLETE":
        code = "waiting_publication"
    elif scope == "history":
        code = "historical_gap"
    return {
        "code": code,
        "status": state,
        "scope": scope,
        "prices_start_at": activation.isoformat() if activation else None,
        "local_prices_start_at": activation.astimezone(zone).isoformat(timespec="minutes")
        if activation
        else None,
        "affected_period": report.get("affected_period") or day,
        "missing_components": missing,
        "reason": result.reason or report.get("reason"),
        "required_action": report.get("required_action"),
        "next_scheduled_update": coordinator.schedule.next_update(now).isoformat(),
    }


def explanation(facts, labels):
    """Localize prose for native review/details; enum states localize in HA itself."""
    return labels["availability_" + facts["code"]].format(
        time=facts["local_prices_start_at"] or "—",
        period=facts["affected_period"],
        components=", ".join(labels.get(key, key) for key in facts["missing_components"]) or "—",
    )


def technical_entity(unique_id, site_id):
    """Only the existing canonical diagnostics, never normal price/status entities."""
    return unique_id in {
        f"{site_id}_{suffix}"
        for suffix in (
            "current_price",
            "next_price",
            "readiness",
            "tomorrow_status",
            "today_minimum",
            "today_maximum",
            "today_average",
            "raw_spot_0",
            "raw_spot_1",
        )
    }
