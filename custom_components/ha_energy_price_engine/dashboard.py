"""Authenticated bounded price-card reads of cached records; never price I/O."""

import json
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .api import PriceAPI
from .const import DOMAIN
from .price_engine import day_bounds
from .status import availability, quarter, statistics

CARD_URL = "/ha_energy_price_engine/energy-price-engine-card.js"
COMPONENTS = ("spot", "dso", "energinet_net", "energinet_system", "supplier", "electricity_tax")


async def async_setup_dashboard(hass):
    websocket_api.async_register_command(hass, websocket_sites)
    websocket_api.async_register_command(hass, websocket_schedule)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL, str(Path(__file__).parent / "www/energy-price-engine-card.js"), False
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


def _summary(window):
    return {
        "status": str(window.status),
        "expected_slots": window.expected_slots,
        "stored_slots": window.available_slots,
        "reason": window.reason,
        "last_success": window.verified_at.isoformat() if window.verified_at else None,
    }


def price_schedule(c, now=None):
    now = now or dt_util.utcnow()
    site = c.site
    zone = ZoneInfo(site["timezone"])
    today = now.astimezone(zone).date()
    api = PriceAPI(c.hass)
    days = []
    provenance = {}
    references = {}
    for offset in (0, 1):
        date = today + timedelta(days=offset)
        first, last = day_bounds(date, site["timezone"])
        window = api.lookup(site["id"], first, last, now=now)
        records = {r.start: r for r in c.price_engine.lookup(site["id"], first, last)}
        raw = {r.start: r for r in c.price_updater.raw_slots.get(str(date), ())}
        report = c.schedule.days.get(site["id"], {}).get(str(date), {})
        raw_report = report.get("raw", {})
        stamp = dt_util.parse_datetime(raw_report.get("verified_at") or "")
        fresh = (
            stamp
            and 0 <= (now - stamp).total_seconds() <= 86400
            and raw_report.get("status") in {"READY", "INCOMPLETE"}
        )
        rows = []
        cursor = first
        while cursor < last:
            end = cursor + timedelta(minutes=15)
            result = api.lookup(site["id"], cursor, end, now=now)
            record = records.get(cursor)
            row = {
                **_instant(cursor, end, zone),
                **{k: None for k in (*COMPONENTS, "vat", "final", "stored_final")},
                "status": str(result.status),
                "reason": result.reason,
                "raw_status": "INCOMPLETE",
                "raw_verified_at": None,
                "revision": None,
                "provenance": None,
            }
            if record:
                parts = json.loads(record.components_json)["components"]
                source = json.loads(record.source_json)
                metadata = {
                    k: {a: v for a, v in p.items() if a not in {"ex_vat", "vat", "incl_vat"}}
                    for k, p in parts.items()
                }
                ref = (record.source_json, json.dumps(metadata, sort_keys=True))
                if ref not in references:
                    key = str(len(references) + 1)
                    references[ref] = key
                    provenance[key] = {"source": source, "components": metadata}
                row.update(
                    provenance=references[ref],
                    revision=record.revision,
                    stored_final=record.final_price_incl_vat * 100,
                )
                for key in COMPONENTS:
                    if key in parts:
                        row[key] = parts[key]["ex_vat"] * 100
                row["vat"] = sum(p["vat"] for p in parts.values()) * 100
                if result.slots:
                    row["final"] = row["stored_final"]
                if end <= now:
                    row.update(raw_status="READY", raw_verified_at=source.get("verified_at"))
            if fresh and cursor in raw:
                if row["spot"] is None:
                    row["spot"] = raw[cursor].price * 100
                if row["spot"] == raw[cursor].price * 100:
                    row.update(raw_status="READY", raw_verified_at=raw_report["verified_at"])
            rows.append(row)
            cursor = end
        days.append(
            {
                "date": str(date),
                **_instant(first, last, zone),
                **_summary(window),
                "slots": rows,
                "ready_slots": sum(r["final"] is not None for r in rows),
                "raw_ready_slots": sum(r["raw_status"] == "READY" for r in rows),
                "raw_report": raw_report,
                "missing_components": report.get("missing_components", []),
                "required_action": report.get("required_action"),
                "failure_stage": report.get("failure_stage"),
                "affected_period": report.get("affected_period"),
            }
        )
    tariffs = []
    grid = c.price_updater.grid_slots.get(str(today), {})
    report = c.schedule.days.get(site["id"], {}).get(str(today), {})
    for slot in days[0]["slots"]:
        part = (
            grid.get(dt_util.parse_datetime(slot["start"]))
            if report.get("failure_stage") not in {"source", "grid"}
            else None
        )
        evidence = {
            "value": part["ex_vat"] * 100 if part else None,
            "status": "READY" if part else "INCOMPLETE",
            "source": part.get("source") if part else None,
            "verified_on": part.get("verified_on") if part else None,
            "verified_at": report.get("grid_source", {}).get("fetched_at"),
            "valid_from": part.get("valid_from") if part else None,
            "valid_to": part.get("valid_to") if part else None,
        }
        previous = (
            {
                k: v
                for k, v in tariffs[-1].items()
                if k not in {"start", "end", "local_start", "local_end"}
            }
            if tariffs
            else None
        )
        if tariffs and previous == evidence:
            tariffs[-1].update(end=slot["end"], local_end=slot["local_end"])
        else:
            tariffs.append(
                {**{k: slot[k] for k in ("start", "end", "local_start", "local_end")}, **evidence}
            )
    return {
        "schema_version": 2,
        "unit": "øre/kWh",
        "component_basis": "ex_vat",
        "final_basis": "incl_vat",
        "site": {k: site[k] for k in ("id", "name", "timezone", "area", "dso_mode")},
        "generated_at": now.isoformat(),
        "current_start": quarter(now)[0].isoformat(),
        "revision": c.price_engine.revisions.get(site["id"], 0),
        "next_scheduled_update": c.schedule.next_update(now).isoformat(),
        "current": _summary(api.lookup(site["id"], *quarter(now), now=now)),
        "next": _summary(api.lookup(site["id"], *quarter(now, 1), now=now)),
        "statistics": statistics(c, now),
        "availability": availability(c, now),
        "days": days,
        "dso_today": tariffs,
        "provenance": provenance,
    }


def _readable(hass, connection):
    registry = er.async_get(hass)
    result = []
    for c in hass.data.get(DOMAIN, {}).values():
        entity = registry.async_get_entity_id("sensor", DOMAIN, f"{c.site['id']}_availability")
        if entity and connection.user.permissions.check_entity(entity, POLICY_READ):
            result.append((c, entity))
    return result


@websocket_api.websocket_command({vol.Required("type"): "ha_energy_price_engine/sites"})
@callback
def websocket_sites(hass, connection, msg):
    connection.send_result(
        msg["id"],
        [
            {"site_id": c.site["id"], "name": c.site["name"], "entity_id": entity}
            for c, entity in _readable(hass, connection)
        ],
    )


@websocket_api.websocket_command(
    {vol.Required("type"): "ha_energy_price_engine/price_schedule", vol.Optional("site_id"): str}
)
@callback
def websocket_schedule(hass, connection, msg):
    sites = _readable(hass, connection)
    selected = msg.get("site_id")
    matches = (
        [c for c, _ in sites if c.site["id"] == selected] if selected else [c for c, _ in sites]
    )
    if len(matches) != 1:
        connection.send_error(
            msg["id"], "select_site", "Select one readable Energy Price Engine site"
        )
        return
    connection.send_result(msg["id"], price_schedule(matches[0]))
