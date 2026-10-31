"""Independent price-only runtime, publication events and source-change monitoring."""

import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .configuration import settings, validate_site
from .const import DOMAIN, PRICE_REVISION_EVENT
from .price_engine import PriceEngine
from .price_schedule import PriceSchedule
from .price_update import PriceUpdater

LOGGER = logging.getLogger(__name__)


class PriceCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, LOGGER, config_entry=entry, name=DOMAIN, always_update=True)
        self.entry = entry
        self.settings_current = True
        self.site = validate_site(settings(entry))
        self.price_engine = PriceEngine(hass, entry.entry_id)
        self.price_updater = PriceUpdater(hass, self.price_engine, self._changed)
        reused = hass.data.get(DOMAIN + "_reload_sources", {}).pop(entry.entry_id, None)
        self.reuse_sources = reused is not None
        if reused is not None:
            self.price_updater.official = reused
        self.schedule = PriceSchedule(self)
        self.pending = None
        self.stopped = False
        self.source_unsub = None
        self.source_entities = set()

    def _changed(self, site_id, records):
        self.hass.bus.async_fire(
            PRICE_REVISION_EVENT,
            {
                "api_version": 2,
                "site_id": site_id,
                "revision": self.price_engine.revisions[site_id],
                "affected_slots": [r.start.isoformat() for r in records],
                "start": records[0].start.isoformat(),
                "end": records[-1].end.isoformat(),
            },
        )

    async def start(self):
        await self.price_engine.async_load([self.site["id"]])
        await self.price_updater.tariffs.load()
        await self.schedule.startup(force=not self.reuse_sources)
        self.schedule.listen()
        self.entry.async_on_unload(self.stop)
        self._watch_source_entities()
        source_entry = self.hass.config_entries.async_get_entry(self.site["nordpool_entry"])
        if source_entry is not None:
            self.entry.async_on_unload(
                source_entry.async_on_state_change(self._provider_state_changed)
            )
        self.entry.async_on_unload(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self._source_registry_changed
            )
        )
        await self.async_refresh()

    @callback
    def _watch_source_entities(self):
        if self.source_unsub:
            self.source_unsub()
            self.source_unsub = None
        registry = er.async_get(self.hass)
        self.source_entities = {
            e.entity_id
            for e in er.async_entries_for_config_entry(registry, self.site["nordpool_entry"])
        }
        if self.source_entities:
            self.source_unsub = async_track_state_change_event(
                self.hass, list(self.source_entities), self._source_changed
            )

    @callback
    def _source_registry_changed(self, event):
        entity = er.async_get(self.hass).async_get(event.data.get("entity_id"))
        if event.data.get("entity_id") in self.source_entities or (
            entity is not None and entity.config_entry_id == self.site["nordpool_entry"]
        ):
            self._watch_source_entities()
            self._source_changed(event)

    @callback
    def _provider_state_changed(self):
        if self.stopped:
            return
        source = self.hass.config_entries.async_get_entry(self.site["nordpool_entry"])
        self._watch_source_entities()
        if source and source.state == ConfigEntryState.LOADED:
            self.price_updater.official.attempts.clear()
        else:
            for report in self.schedule.days.get(self.site["id"], {}).values():
                report.update(status="STALE", reason="Official Nord Pool entry is not loaded")
                report.get("raw", {}).update(status="STALE")
            self.entry.async_create_task(
                self.hass, self.async_request_refresh(), "Publish provider readiness"
            )
        self._source_changed(None)

    @callback
    def _source_changed(self, event):
        if self.pending or self.stopped:
            return

        async def verify(_):
            self.pending = None
            if self.stopped:
                return
            # Coalesce state notifications; the adapter enforces its 15-minute
            # attempt backoff. Mandatory publication times use force=True.
            now = dt_util.utcnow()
            today = now.astimezone(ZoneInfo(self.site["timezone"])).date()
            self.price_updater.official.invalidated.update(self.price_updater.official.cache)
            for day in (today, today + timedelta(days=1)):
                await self.schedule.refresh_day(self.site, day, now, force=False)
            await self.async_request_refresh()

        self.pending = async_call_later(self.hass, 60, verify)

    def stop(self):
        self.stopped = True
        self.schedule.stop()
        if self.source_unsub:
            self.source_unsub()
            self.source_unsub = None
        if self.pending:
            self.pending()
            self.pending = None

    async def _async_update_data(self):
        reports = self.schedule.days.get(self.site["id"], {})
        today = str(dt_util.utcnow().astimezone(ZoneInfo(self.site["timezone"])).date())
        report = reports.get(today, {"status": "INCOMPLETE"})
        return report
