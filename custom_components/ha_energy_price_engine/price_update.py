"""Source refresh/composition boundary, separate from all lookup consumers."""

from asyncio import Lock
from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .adapters import parse_prices
from .configuration import tariff_for
from .price_components import active_hours, danish_public_components
from .price_engine import day_bounds
from .prices import OfficialPrices
from .sources import validate_entity_source
from .tariff_source import TariffSource


class PriceUpdater:
    def __init__(self, hass, engine, on_change=None):
        self.hass, self.engine = hass, engine
        self.official = OfficialPrices(hass)
        self.tariffs = TariffSource(hass, engine.entry_id)
        self.status = {}
        self.raw_reports, self.raw_slots = {}, {}
        self.lock = Lock()
        self.on_change = on_change

    def state(self, entity_id, now, minutes):
        entry = er.async_get(self.hass).async_get(entity_id)
        if entry and entry.platform == "ha_energy_price_engine":
            raise ValueError("Integration output cannot be its own price source")
        state = self.hass.states.get(entity_id)
        if (
            state is None
            or state.state in {"unknown", "unavailable", ""}
            or not 0 <= (now - state.last_reported).total_seconds() <= minutes * 60
        ):
            raise ValueError("Price/tariff source missing or stale")
        return state

    async def refresh(self, site, now, *, force=False, dates=None):
        async with self.lock:
            key = site["id"]
            cutoff = str(now.astimezone(ZoneInfo(site["timezone"])).date() - timedelta(days=1))
            self.raw_slots = {day: rows for day, rows in self.raw_slots.items() if day >= cutoff}
            self.raw_reports = {
                day: report for day, report in self.raw_reports.items() if day >= cutoff
            }
            old = self.status.get(key, {})
            report = {
                "last_success": old.get("last_success"),
                "missing_components": [],
                "failure_stage": None,
                "required_action": None,
                "affected_period": None,
                "reason": None,
                "last_attempt": now.isoformat(),
                "status": "ERROR",
                "source_slots": None,
            }
            self.status[key] = report
            stage = "source"
            try:
                tariff = tariff_for(site) if "vat" in site else dict(site.get("tariff", {}))
                if site.get("nordpool_entry"):
                    slots = await self.official.get(
                        site, now, compose=False, force=force, dates=dates
                    )
                    if not slots and self.official.last_errors:
                        raise ValueError("Official Nord Pool source failed; stored prices retained")
                    source = {
                        "kind": "nordpool",
                        "config_entry": site["nordpool_entry"],
                        "area": site.get("area", "DK2"),
                        "input_unit": "DKK/MWh",
                        "input_vat": "excluded",
                    }
                else:
                    state = self.state(site["price_entity"], now, site.get("stale_minutes", 40))
                    slots = parse_prices(
                        dict(state.attributes),
                        site.get("price_attribute", "slots"),
                        site.get("price_multiplier", 1),
                    )
                    source = {
                        "kind": "entity",
                        "entity_id": site["price_entity"],
                        "multiplier": site.get("price_multiplier", 1),
                        "input_vat": tariff.get("mode", "all_in"),
                    }
                if site.get("nordpool_entry"):
                    times = [
                        timestamp
                        for (entry, area, requested), (
                            timestamp,
                            data,
                        ) in self.official.cache.items()
                        if entry == site["nordpool_entry"]
                        and area == site.get("area", "DK2")
                        and data
                        and (not dates or requested in {str(day) for day in dates})
                    ]
                    source["verified_at"] = min(times).isoformat() if times else now.isoformat()
                else:
                    verified = (
                        validate_entity_source(state, site, now)
                        if site.get("source_type") == "entity"
                        else state.last_reported
                    )
                    source["verified_at"] = verified.isoformat()
                    source["input_unit"] = site.get("price_unit", "explicit_multiplier")
                # Source publication precedes *all* component/grid/storage work.
                days = dates or [
                    now.astimezone(ZoneInfo(site["timezone"])).date() + timedelta(days=n)
                    for n in (0, 1)
                ]
                for day in days:
                    start, end = day_bounds(day, site["timezone"])
                    selected = tuple(s for s in slots if start <= s.start and s.end <= end)
                    expected = int((end - start).total_seconds() / 900)
                    fresh = not (
                        site.get("nordpool_entry") and str(day) in self.official.last_errors
                    )
                    self.raw_slots[str(day)] = selected
                    self.raw_reports[str(day)] = {
                        "status": "STALE"
                        if not fresh
                        else "READY"
                        if len(selected) == expected
                        else "INCOMPLETE",
                        "valid_slots": len(selected),
                        "expected_slots": expected,
                        "verified_at": source["verified_at"],
                        "last_attempt": now.isoformat(),
                        "price_basis": site.get("price_basis", "spot_ex_vat"),
                        "reason": None
                        if fresh
                        else "Nord Pool refresh failed; cached raw source retained",
                    }
                if dates:
                    verified_slots = []
                    for day in dates:
                        start, end = day_bounds(day, site["timezone"])
                        selected = [s for s in slots if start <= s.start and s.end <= end]
                        report["source_slots"] = len(selected)
                        complete = (
                            bool(selected)
                            and selected[0].start == start
                            and selected[-1].end == end
                            and all(a.end == b.start for a, b in zip(selected, selected[1:]))
                        )
                        if not complete:
                            report.update(
                                status="INCOMPLETE",
                                reason="Requested day source series is incomplete",
                                failure_stage="source",
                                required_action="Check raw source coverage; verify the selected Nord Pool area and wait for publication or recheck the source.",
                                changed=False,
                            )
                            return False
                        verified_slots.extend(selected)
                    if site.get("nordpool_entry") and len(verified_slots) != len(slots):
                        raise ValueError("Source returned intervals outside the requested dates")
                    slots = verified_slots
                stage = "configuration"
                if site.get("grid_tariff_entity"):
                    stage = "grid"
                    state = self.state(
                        site["grid_tariff_entity"], now, site.get("stale_minutes", 40)
                    )
                    tariff["grid_slots"] = parse_prices(dict(state.attributes), "slots")
                locked_dso = all(
                    any(
                        r["id"] == "dso"
                        and slot.start.astimezone(ZoneInfo(site["timezone"])).hour
                        in active_hours(r)
                        and r.get("locked")
                        and r["valid_from"]
                        <= str(slot.start.astimezone(ZoneInfo(site["timezone"])).date())
                        < r["valid_to"]
                        for r in site.get("dated_components", [])
                    )
                    for slot in slots
                )
                if site.get("dso_mode", "manual") != "manual" and slots and not locked_dso:
                    if (
                        tariff.get("mode") not in {"spot_ex_vat", "spot_incl_vat"}
                        or tariff.get("grid", 0)
                        or site.get("grid_tariff_entity")
                    ):
                        raise ValueError(
                            "Automatic DSO requires spot basis without duplicate grid additions"
                        )
                    stage = "grid"
                    try:
                        tariff["grid_slots"], source["dso"] = await self.tariffs.get(
                            site, slots[0].start, slots[-1].end, now
                        )
                    except ValueError:
                        if not site.get("dso_manual_fallback"):
                            raise
                        # Fallback must be an explicit dated DSO rule, never zero.
                        tariff.pop("grid", None)
                        source["dso"] = {
                            "provider": "manual_fallback",
                            "warning": "Automatic tariff unavailable",
                            "unit": "DKK/kWh ex VAT",
                        }
                if site.get("dated_components") is not None and tariff.get("mode") != "all_in":
                    tariff["components"] = list(site["dated_components"])
                    if site.get("danish_public_rates"):
                        tariff["components"] = danish_public_components() + tariff["components"]
                    tariff.update(
                        timezone=site["timezone"],
                        heating_registered=site.get("heating_registered", False),
                        annual_usage_kwh=site.get("annual_usage_kwh", 0),
                        usage_year=site.get("usage_year"),
                    )
                stage = "composition"
                report["grid_status"] = "STALE" if source.get("dso", {}).get("warning") else "READY"
                before = {r.start: r.final_price_incl_vat for r in self.engine.records.get(key, ())}
                changed = await self.engine.async_update(key, slots, tariff, source, now)
                affected = tuple(
                    r
                    for r in self.engine.records.get(key, ())
                    if r.start >= now and before.get(r.start) != r.final_price_incl_vat
                )
                if affected and self.on_change:
                    self.on_change(key, affected)
                day = dates[0] if dates else now.astimezone(ZoneInfo(site["timezone"])).date()
                report.update(
                    status="READY"
                    if self.engine.complete_day(key, day, site["timezone"])
                    else "INCOMPLETE",
                    last_success=source["verified_at"],
                    reason=None,
                    failure_stage=None,
                    missing_components=[],
                    required_action=None,
                    affected_period=None,
                    changed=changed,
                )
                if site.get("nordpool_entry") and self.official.last_errors:
                    report.update(
                        status="STALE",
                        reason="Nord Pool refresh failed; retained verified intervals",
                        failure_stage="source",
                        required_action="Check official Nord Pool availability and recheck. Retained raw intervals have their original verification timestamp; final prices are not READY.",
                    )
                if source.get("dso", {}).get("warning"):
                    report.update(
                        status="STALE",
                        reason=source["dso"]["warning"],
                        failure_stage="grid",
                        required_action="Recheck Radius/grid coverage and cache age, or configure verified dated manual tariffs. Cached/fallback prices are not certified READY.",
                    )
                return changed
            except (
                ValueError,
                TypeError,
                KeyError,
                OSError,
                HomeAssistantError,
                TimeoutError,
            ) as err:
                period = ", ".join(map(str, dates)) if dates else "current/next delivery day"
                stage = (
                    "configuration"
                    if getattr(err, "components", None)
                    else "storage"
                    if isinstance(err, OSError) and stage == "composition"
                    else stage
                )
                if stage == "source":
                    for day in dates or [now.astimezone(ZoneInfo(site["timezone"])).date()]:
                        self.raw_reports[str(day)] = {
                            "status": "ERROR",
                            "valid_slots": 0,
                            "expected_slots": int(
                                (
                                    day_bounds(day, site["timezone"])[1]
                                    - day_bounds(day, site["timezone"])[0]
                                ).total_seconds()
                                / 900
                            ),
                            "reason": str(err),
                            "last_attempt": now.isoformat(),
                        }
                        self.raw_slots.pop(str(day), None)
                report.update(
                    status="INCOMPLETE" if stage == "configuration" else "ERROR",
                    reason=str(err),
                    failure_stage=stage,
                    changed=False,
                    affected_period=getattr(err, "period", period),
                    missing_components=getattr(err, "components", []),
                    required_action=getattr(
                        err,
                        "action",
                        "Check the selected source and its availability, units and verification timestamp, then Configure → guided setup and Save & verify. Retained prices are not certified READY.",
                    ),
                )
                return False  # Keep the last durable verified prices, never invent zeros.
