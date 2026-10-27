"""Civil-time publication refresh, conditional retries and restart recovery."""

import logging
from asyncio import Lock
from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.core import callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .price_engine import day_bounds

LOGGER = logging.getLogger(__name__)

TIMES = ((0, 1), (13, 5), (13, 20), (13, 40), (23, 59))
ZONE = ZoneInfo("Europe/Copenhagen")


class PriceSchedule:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self.store = Store(
            self.hass, 1, f"ha_energy_price_engine.{coordinator.entry.entry_id}.price_schedule"
        )
        self.work_lock = Lock()
        self.days = {}
        self.cancel = None
        self.active = False

    def complete(self, site, day, now=None):
        key = site["id"]
        report = self.days.get(key, {}).get(str(day), {})
        try:
            verified = dt_util.parse_datetime(report.get("last_success", ""))
            fresh = (
                verified is not None
                and verified.tzinfo is not None
                and 0 <= ((now or dt_util.utcnow()) - verified).total_seconds() <= 86400
            )
        except ValueError, TypeError:
            fresh = False
        return (
            self.coordinator.price_engine.complete_day(key, day, site["timezone"])
            and report.get("status") == "READY"
            and fresh
        )

    async def refresh_day(self, site, day, now, *, force=True):
        async with self.work_lock:
            if getattr(self.coordinator, "stopped", False):
                return False
            return await self._refresh_day(site, day, now, force=force)

    async def _refresh_day(self, site, day, now, *, force=True):
        key = site["id"]
        changed = await self.coordinator.price_updater.refresh(site, now, force=force, dates=[day])
        start, end = day_bounds(day, site["timezone"])
        rows = self.coordinator.price_engine.lookup(key, start, end)
        report = self.coordinator.price_updater.status[key]
        complete = self.coordinator.price_engine.complete_day(key, day, site["timezone"])
        scoped = bool(
            site.get("pricing_start")
            and report.get("verified_from")
            and report.get("verified_until")
        )
        state = (
            "READY"
            if (complete or scoped) and report["status"] == "READY"
            else report["status"]
            if report["status"] in {"ERROR", "STALE"}
            else "INCOMPLETE"
        )
        previous = self.days.get(key, {}).get(str(day), {})
        if day == now.astimezone(ZONE).date() and state != "READY":
            LOGGER.warning("Current-day price table not verified: %s", state)
        self.days.setdefault(key, {})[str(day)] = {
            "status": state,
            "requested_date": str(day),
            "last_attempt": now.isoformat(),
            "last_success": report.get("last_success")
            if state == "READY"
            else previous.get("last_success"),
            "valid_slots": len(rows) if state == "READY" else 0,
            "stored_slots": len(rows),
            "expected_slots": int((end - start).total_seconds() / 900),
            "reason": report.get("reason"),
            "failure_stage": report.get("failure_stage"),
            "source_slots": report.get("source_slots"),
            "grid_status": report.get("grid_status"),
            "verified_from": report.get("verified_from"),
            "verified_until": report.get("verified_until"),
            "required_action": report.get("required_action"),
            "missing_components": report.get("missing_components", []),
            "affected_period": report.get("affected_period"),
        }
        # Keep a bounded operational log; price history has independent retention.
        self.days[key] = {
            d: r for d, r in self.days[key].items() if d >= str(day - timedelta(days=7))
        }
        await self.store.async_save(self.days)
        return changed

    async def startup(self, *, force=True):
        self.days = await self.store.async_load() or {}
        now = dt_util.utcnow()
        for optimizer in self.coordinator.sites.values():
            site = optimizer.site
            today = now.astimezone(ZoneInfo(site["timezone"])).date()
            # Always verify current day; also reconcile known/missing next day.
            for day in (today, today + timedelta(days=1)):
                await self.refresh_day(site, day, now, force=force)

    async def run(self, now, hour, minute):
        changed = False
        attempted = False
        for optimizer in self.coordinator.sites.values():
            site = optimizer.site
            today = now.astimezone(ZoneInfo(site["timezone"])).date()
            day = today if (hour, minute) == (0, 1) else today + timedelta(days=1)
            unconditional = (hour, minute) in {(0, 1), (13, 5)}
            if unconditional or not self.complete(site, day, now):
                attempted = True
                changed = await self.refresh_day(site, day, now) or changed
        if attempted:
            await self.coordinator.async_request_refresh()
        return changed

    def listen(self):
        self.active = True
        self._arm()
        self.coordinator.entry.async_on_unload(self.stop)

    def stop(self):
        self.active = False
        if self.cancel:
            self.cancel()
            self.cancel = None

    def next_update(self, now=None):
        now = now or dt_util.utcnow()
        local = now.astimezone(ZONE)
        choices = []
        for offset in (0, 1):
            for hour, minute in TIMES:
                candidate = (local + timedelta(days=offset)).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                if candidate > local:
                    choices.append(candidate)
        return min(choices)

    def _arm(self):
        target = self.next_update()

        async def run_and_arm():
            try:
                await self.run(dt_util.utcnow(), target.hour, target.minute)
            finally:
                if self.active:
                    self._arm()

        @callback
        def fire(_):
            self.coordinator.entry.async_create_task(
                self.hass, run_and_arm(), "Refresh price publication"
            )

        self.cancel = async_track_point_in_utc_time(self.hass, fire, target)
