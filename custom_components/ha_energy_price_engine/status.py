"""Shared, compact read-only views of the precomputed quarter-hour schedule."""

import json
from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .api import PriceAPI, Status
from .price_engine import day_bounds


def quarter(now, offset=0):
    first = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0) + timedelta(
        minutes=15 * offset
    )
    return first, first + timedelta(minutes=15)


def report(c, day):
    return c.schedule.days.get(c.site["id"], {}).get(str(day), {})


def price(c, offset=0, now=None):
    return PriceAPI(c.hass).lookup(c.site["id"], *quarter(now or dt_util.utcnow(), offset), now=now)


def statistics(c, now=None):
    """No Recorder samples or invented past rates; average exact schedule slots."""
    now = now or dt_util.utcnow()
    first, last = day_bounds(
        now.astimezone(ZoneInfo(c.site["timezone"])).date(), c.site["timezone"]
    )
    api = PriceAPI(c.hass)
    full = api.lookup(c.site["id"], first, last, now=now)
    selected, scope = full, "full_day"
    if full.status != Status.READY:
        candidates = [
            r.start
            for r in c.price_engine.lookup(c.site["id"], quarter(now)[0], last)
            if r.start >= quarter(now)[0]
        ]
        selected = None
        if candidates:
            remaining = api.lookup(c.site["id"], candidates[0], last, now=now)
            if remaining.status == Status.READY:
                selected, scope = remaining, "remaining_day"
    facts = {
        "scope": scope if selected and selected.status == Status.READY else "unavailable",
        "used_slots": 0,
        "day_slots": full.expected_slots,
        "reason": full.reason,
        "start": None,
        "end": last.isoformat(),
    }
    if selected and selected.status == Status.READY:
        values = [q.price for q in selected.slots]
        facts.update(
            used_slots=len(values),
            start=selected.slots[0].start.isoformat(),
            average=sum(values) / len(values),
            minimum=min(values),
            maximum=max(values),
            reason=None,
        )
    return facts


def breakdown(c, now=None):
    now = now or dt_util.utcnow()
    for offset, label in ((0, "current_quarter"), (1, "next_quarter")):
        window = price(c, offset, now)
        if window.status != Status.READY:
            continue
        row = c.price_engine.lookup(c.site["id"], *quarter(now, offset))[0]
        parts = json.loads(row.components_json)["components"]
        return {
            "period": label,
            "start": row.start.isoformat(),
            "end": row.end.isoformat(),
            "unit": "øre/kWh",
            "revision": row.revision,
            "source": json.loads(row.source_json),
            "components": {k: {**p, "value_ore": p["ex_vat"] * 100} for k, p in parts.items()},
            "vat_amount_ore": sum(p["vat"] for p in parts.values()) * 100,
            "final_ore": row.final_price_incl_vat * 100,
        }
    return {"period": "unavailable", "components": {}}


def source_value(c, kind, now=None):
    now = now or dt_util.utcnow()
    first, last = quarter(now, int(kind == "next_spot"))
    day = first.astimezone(ZoneInfo(c.site["timezone"])).date()
    raw = report(c, day).get("raw", {})
    try:
        stamp = dt_util.parse_datetime(raw.get("verified_at", ""))
        fresh = stamp and 0 <= (now - stamp).total_seconds() <= 86400
    except TypeError, ValueError:
        fresh = False
    if kind in {"current_spot", "next_spot"}:
        if not fresh or raw.get("status") not in {"READY", "INCOMPLETE"}:
            return None
        return next(
            (
                s.price
                for s in c.price_updater.raw_slots.get(str(day), ())
                if s.start == first and s.end == last
            ),
            None,
        )
    if report(c, day).get("failure_stage") in {"source", "grid"}:
        return None
    part = c.price_updater.grid_slots.get(str(day), {}).get(first)
    return part["ex_vat"] if part else None


def availability(c, now=None):
    now = now or dt_util.utcnow()
    day = now.astimezone(ZoneInfo(c.site["timezone"])).date()
    current, following = price(c, 0, now), price(c, 1, now)
    tomorrow = PriceAPI(c.hass).lookup(
        c.site["id"], *day_bounds(day + timedelta(days=1), c.site["timezone"]), now=now
    )
    r = report(c, day)
    code = (
        "ready"
        if current.status == Status.READY
        else "error"
        if current.status == Status.ERROR
        else "stale"
        if current.status == Status.STALE
        else "waiting"
        if following.status == Status.READY
        else "missing"
    )
    facts = {
        "code": code,
        "current_status": str(current.status),
        "next_status": str(following.status),
        "tomorrow_status": str(tomorrow.status),
        "current_slots": current.available_slots,
        "next_slots": following.available_slots,
        "tomorrow_slots": tomorrow.available_slots,
        "tomorrow_expected": tomorrow.expected_slots,
        "available_from": following.slots[0]
        .start.astimezone(ZoneInfo(c.site["timezone"]))
        .isoformat(timespec="minutes")
        if following.status == Status.READY
        else None,
        "reason": current.reason or r.get("reason"),
        "action": r.get("required_action"),
        "missing_components": r.get("missing_components", []),
        "statistics": statistics(c, now),
        "breakdown": breakdown(c, now),
        "next_check": c.schedule.next_update(now).isoformat(),
    }
    return facts
