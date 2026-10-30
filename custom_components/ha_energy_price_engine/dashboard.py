"""Bounded, authenticated dashboard reads of stored prices, never tariff arithmetic.

This frontend transport is separate from the stable CM Python API v1. It creates
no Recorder states, provider requests, SQL connections, or control/write actions.
"""

import json
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .api import ConsumerAPI
from .const import DOMAIN
from .device_diagnostics import availability
from .price_engine import day_bounds

CARD_URL = "/ha_energy_price_engine/energy-price-engine-card.js"
COMPONENTS = ("spot", "dso", "energinet_net", "energinet_system", "supplier", "electricity_tax")


async def async_setup_dashboard(hass):
    websocket_api.async_register_command(hass, websocket_schedule)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL, str(Path(__file__).parent / "www" / "energy-price-engine-card.js"), False
            )
        ]
    )


def _instant(start, end, zone):
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "local_start": start.astimezone(zone).isoformat(timespec="minutes"),
        "local_end": end.astimezone(zone).isoformat(timespec="minutes"),
    }


def _summary(result):
    return {
        "status": str(result.status),
        "expected_slots": result.expected_slots,
        "stored_slots": result.valid_slots,
        "reason": result.reason,
        "last_success": result.last_success,
    }


def price_schedule(coordinator, *, now=None):
    """At most two local days (92/96/100 quarters each), missing quarters explicit.

    Values are unrounded ore/kWh; monetary rounding belongs only to the card. All
    charges and VAT are read from immutable applied component snapshots. A valid
    raw source can be shown even when final composition failed. Retained stale
    records are inspectable but never plotted as verified final prices.
    """
    now = now or dt_util.utcnow()
    site = coordinator.site
    zone = ZoneInfo(site["timezone"])
    today = now.astimezone(zone).date()
    api = ConsumerAPI(coordinator.hass)
    provenance, references = {}, {}
    days = []

    def lookup(start, end):
        return api.lookup(
            site["id"], start, end, now=now, producer_entry_id=coordinator.entry.entry_id
        )

    def reference(record, parts, source):
        # Different spot amounts must not duplicate an entire source/contract
        # snapshot for every quarter. All numeric values already live in rows.
        metadata = {
            name: {k: v for k, v in part.items() if k not in {"ex_vat", "vat", "incl_vat"}}
            for name, part in parts.items()
        }
        key = (json.dumps(metadata, sort_keys=True), record.source_json)
        if key not in references:
            name = str(len(references) + 1)
            references[key] = name
            provenance[name] = {"source": source, "components": metadata}
        return references[key]

    for offset in (0, 1):
        day = today + timedelta(days=offset)
        first, last = day_bounds(day, site["timezone"])
        result = lookup(first, last)
        records = {r.start: r for r in result.records}
        raw = {r.start: r for r in coordinator.price_updater.raw_slots.get(str(day), ())}
        raw_report = coordinator.price_updater.raw_reports.get(str(day), {})
        report = coordinator.schedule.days.get(site["id"], {}).get(str(day), {})
        verified = dt_util.parse_datetime(raw_report.get("verified_at", ""))
        raw_fresh = bool(
            verified
            and 0 <= (now - verified).total_seconds() < 7200
            and raw_report.get("status") in {"READY", "INCOMPLETE"}
            and getattr(coordinator, "settings_current", True)
        )
        slots = []
        start = first
        while start < last:
            end = start + timedelta(minutes=15)
            record = records.get(start)
            state = lookup(start, end)
            row = {
                **_instant(start, end, zone),
                "status": str(state.status),
                "reason": state.reason or (None if record else report.get("reason")),
                "revision": record.revision if record else None,
                "provenance": None,
                **{key: None for key in (*COMPONENTS, "vat", "final", "stored_final")},
                "raw_status": "INCOMPLETE",
                "raw_verified_at": None,
                "calculated_at": record.calculated_at.isoformat() if record else None,
            }
            if record:
                snapshot = json.loads(record.components_json)
                source = json.loads(record.source_json)
                parts = snapshot.get("components", {})
                row["provenance"] = reference(record, parts, source)
                for key in COMPONENTS:
                    if key in parts:
                        row[key] = parts[key]["ex_vat"] * 100
                if parts:
                    row["vat"] = sum(p["vat"] for p in parts.values()) * 100
                row["stored_final"] = record.final_price_incl_vat * 100
                if str(state.status) == "READY":
                    row["final"] = row["stored_final"]
                # Settled spot snapshots remain valid independently of live fetches.
                if row["spot"] is not None:
                    row["raw_status"] = (
                        "READY"
                        if end <= now
                        else "STALE"
                        if str(state.status) == "READY"
                        else str(state.status)
                    )
                    row["raw_verified_at"] = source.get("verified_at")
            # Final component failures must not hide independently verified spot.
            if start in raw and raw_fresh and raw_report.get("price_basis") != "all_in":
                basis = raw_report.get("price_basis")
                raw_value = (
                    raw[start].price * 100 / (1 + site["vat"] if basis == "spot_incl_vat" else 1)
                )
                if row["spot"] is None:
                    row["spot"] = raw_value
                # Preserve the spot actually used by an existing final record.
                if row["spot"] == raw_value:
                    row["raw_status"] = "READY"
                    row["raw_verified_at"] = raw_report.get("verified_at")
            elif start in raw and row["spot"] is None:
                row["raw_status"] = "ERROR" if raw_report.get("status") == "ERROR" else "STALE"
            slots.append(row)
            start = end
        days.append(
            {
                "date": str(day),
                **_instant(first, last, zone),
                **_summary(result),
                "ready_slots": sum(s["status"] == "READY" for s in slots),
                "raw_ready_slots": sum(
                    s["raw_status"] == "READY" and s["spot"] is not None for s in slots
                ),
                "raw_report": dict(raw_report),
                "required_action": report.get("required_action"),
                "missing_components": report.get("missing_components", []),
                "failure_stage": report.get("failure_stage"),
                "affected_period": report.get("affected_period"),
                "slots": slots,
            }
        )

    # Merge only exact equal applied values with equal status/provenance. In
    # particular, displayed rounding must not merge two distinct verified rates.
    tariffs, keys = [], []
    for row in days[0]["slots"]:
        origin = provenance.get(row["provenance"], {})
        part = origin.get("components", {}).get("dso", {})
        source = part.get("source") or origin.get("source", {}).get("dso", {}).get("provider")
        evidence = {
            "source": source,
            "verified_on": part.get("verified_on"),
            "verified_at": origin.get("source", {}).get("dso", {}).get("fetched_at"),
            "valid_from": part.get("valid_from"),
            "valid_to": part.get("valid_to"),
        }
        status = row["status"] if row["dso"] is not None else "INCOMPLETE"
        key = (row["dso"], status, json.dumps(evidence, sort_keys=True))
        if tariffs and keys[-1] == key and tariffs[-1]["end"] == row["start"]:
            tariffs[-1].update(end=row["end"], local_end=row["local_end"])
        else:
            keys.append(key)
            tariffs.append(
                {
                    **{k: row[k] for k in ("start", "end", "local_start", "local_end")},
                    "value": row["dso"],
                    "status": status,
                    **evidence,
                }
            )
    current = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
    return {
        "schema_version": 1,
        "unit": "øre/kWh",
        "component_basis": "ex_vat",
        "final_basis": "incl_vat",
        "site": {
            **{key: site[key] for key in ("id", "name", "timezone", "area")},
            "source_type": site.get("source_type"),
            "dso_mode": site.get("dso_mode"),
        },
        "generated_at": now.isoformat(),
        "current_start": current.isoformat(),
        "revision": coordinator.price_engine.revisions.get(site["id"], 0),
        "next_scheduled_update": coordinator.schedule.next_update(now).isoformat(),
        "current": _summary(lookup(current, current + timedelta(minutes=15))),
        "next": _summary(lookup(current + timedelta(minutes=15), current + timedelta(minutes=30))),
        "availability": {
            scope: availability(coordinator, scope, now=now)
            for scope in ("current", "history", "tomorrow")
        },
        "days": days,
        "dso_today": tariffs,
        "provenance": provenance,
    }


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_energy_price_engine/price_schedule",
        vol.Required("entity_id"): cv.entity_id,
    }
)
@callback
def websocket_schedule(hass, connection, msg):
    """Read one authorized PE site's two-day view; no arbitrary SQL/date export."""
    entity_id = msg["entity_id"]
    if not connection.user.permissions.check_entity(entity_id, POLICY_READ):
        raise Unauthorized(entity_id=entity_id)
    entity = er.async_get(hass).async_get(entity_id)
    coordinator = (
        hass.data.get(DOMAIN, {}).get(entity.config_entry_id)
        if entity and entity.platform == DOMAIN
        else None
    )
    if coordinator is None:
        connection.send_error(
            msg["id"],
            websocket_api.ERR_NOT_FOUND,
            "Select an entity of a loaded Energy Price Engine site",
        )
        return
    connection.send_result(msg["id"], price_schedule(coordinator))
