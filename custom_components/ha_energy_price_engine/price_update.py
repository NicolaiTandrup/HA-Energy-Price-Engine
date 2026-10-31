"""The only fetch/verification/composition boundary; reads use published snapshots."""

from asyncio import Lock
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.exceptions import HomeAssistantError

from .configuration import tariff_for
from .price_engine import day_bounds
from .prices import OfficialPrices
from .tariff_source import TariffSource


class PriceUpdater:
    def __init__(self, hass, engine, on_change=None):
        self.hass, self.engine = hass, engine
        self.official = OfficialPrices(hass)
        self.tariffs = TariffSource(hass, engine.entry_id)
        self.raw_slots = {}
        self.grid_slots = {}
        self.lock = Lock()
        self.on_change = on_change

    async def refresh(self, site, now, *, force=False, dates):
        """A single delivery-day update, used only by the scheduler."""
        async with self.lock:
            report = await self._day(site, dates[0], now, force)
            cutoff = str(now.astimezone(ZoneInfo(site["timezone"])).date() - timedelta(days=1))
            self.raw_slots = {d: v for d, v in self.raw_slots.items() if d >= cutoff}
            self.grid_slots = {d: v for d, v in self.grid_slots.items() if d >= cutoff}
            return report

    async def _day(self, site, day, now, force):
        key = site["id"]
        first, last = day_bounds(day, site["timezone"])
        report = {
            "status": "INCOMPLETE",
            "last_attempt": now.isoformat(),
            "last_success": None,
            "expected_slots": int((last - first).total_seconds() / 900),
            "valid_slots": 0,
            "verified_starts": [],
            "missing_components": [],
            "reason": None,
            "failure_stage": None,
            "required_action": None,
        }
        stage = "source"
        try:
            slots = tuple(
                s
                for s in await self.official.get(site, now, force=force, dates=[day])
                if first <= s.start and s.end <= last
            )
            cached = self.official.cache.get((site["nordpool_entry"], site["area"], str(day)))
            verified = cached[0] if cached else None
            fresh = bool(
                verified
                and 0 <= (now - verified).total_seconds() <= 86400
                and not self.official.last_errors
            )
            self.raw_slots[str(day)] = slots
            report["raw"] = {
                "status": "READY"
                if fresh and len(slots) == report["expected_slots"]
                else "INCOMPLETE"
                if fresh
                else "ERROR",
                "verified_at": verified.isoformat() if verified else None,
                "valid_slots": len(slots),
                "expected_slots": report["expected_slots"],
            }
            if not fresh:
                raise ValueError(
                    "Official Nord Pool verification failed; retained prices are not ready"
                )
            if not slots:
                report.update(
                    reason="Waiting for Nord Pool publication",
                    failure_stage="publication",
                    required_action="Wait for the next scheduled source check; verify the selected area if this persists",
                )
                return report
            source = {
                "kind": "nordpool",
                "config_entry": site["nordpool_entry"],
                "area": site["area"],
                "input_unit": "DKK/MWh",
                "input_vat": "excluded",
                "verified_at": verified.isoformat(),
            }
            tariff = tariff_for(site)
            if site["dso_mode"] == "radius_c":
                stage = "grid"
                tariff["grid_slots"], source["dso"] = await self.tariffs.get(site, first, last, now)
                report["grid_source"] = source["dso"]
                stamp = datetime.fromisoformat(source["dso"]["fetched_at"])
                if stamp.tzinfo is None or stamp > now:
                    raise ValueError("Radius verification timestamp is invalid or future-dated")
                if source["dso"].get("warning"):
                    raise ValueError(source["dso"]["warning"])
            self.grid_slots[str(day)] = {}
            from .price_components import resolved_dso

            cursor = first
            while cursor < last:
                from .models import PriceSlot

                part = resolved_dso(PriceSlot(cursor, cursor + timedelta(minutes=15), 0), tariff)
                if part is not None:
                    self.grid_slots[str(day)][cursor] = part
                cursor += timedelta(minutes=15)
            stage = "composition"
            before = {r.start: r.revision for r in self.engine.records.get(key, ())}
            result = await self.engine.async_update(key, slots, tariff, source, now)
            report.update(
                status="READY"
                if len(result.verified_starts) == report["expected_slots"]
                else "INCOMPLETE",
                last_success=verified.isoformat(),
                verified_starts=list(result.verified_starts),
                valid_slots=len(result.verified_starts),
                missing_components=sorted({c for items in result.missing.values() for c in items}),
            )
            if result.missing:
                report.update(
                    reason="Some intervals lack a verified tariff or contract",
                    failure_stage="configuration",
                    affected_period=next(iter(result.missing)),
                    required_action="Configure the affected component and its actual effective period; earlier unknown rates are never assumed",
                )
            elif report["status"] != "READY":
                report.update(
                    reason="Source does not cover the complete delivery day",
                    failure_stage="coverage",
                    required_action="Check Nord Pool coverage and the next scheduled publication",
                )
            affected = tuple(
                r
                for r in self.engine.records.get(key, ())
                if r.start >= now and r.revision != before.get(r.start)
            )
            if affected and self.on_change:
                self.on_change(key, affected)
            report["changed"] = result.changed
            return report
        except (ValueError, TypeError, KeyError, OSError, HomeAssistantError, TimeoutError) as err:
            if stage == "source":
                report["raw"] = {
                    "status": "ERROR",
                    "valid_slots": 0,
                    "verified_at": None,
                    "reason": str(err),
                }
            if isinstance(err, OSError) and stage == "composition":
                stage = "storage"
            report.update(
                status="ERROR",
                reason=str(err),
                failure_stage=stage,
                affected_period=str(day),
                required_action="Check disk space/recovery before retrying"
                if stage == "storage"
                else "Check the selected source or verified tariff and use Check prices",
            )
            return report
