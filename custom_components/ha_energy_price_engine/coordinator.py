"""Independent price-only runtime, publication events and durable configuration audit."""

import logging
from datetime import timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .configuration import settings, tariff_for, validate_site
from .const import DOMAIN, PRICE_REVISION_EVENT
from .price_components import active_hours
from .price_engine import PriceEngine
from .price_schedule import PriceSchedule
from .price_update import PriceUpdater
from .tariff_source import RADIUS_CODE, RADIUS_GLN, normalize_tariffs

LOGGER = logging.getLogger(__name__)


class PriceCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, LOGGER, config_entry=entry, name=DOMAIN, always_update=True)
        self.entry = entry
        self.site = validate_site(settings(entry))
        self.sites = {self.site["id"]: SimpleNamespace(site=self.site)}
        self.price_engine = PriceEngine(hass, entry.entry_id)
        self.price_updater = PriceUpdater(hass, self.price_engine, self._changed)
        self.schedule = PriceSchedule(self)
        self.pending = None
        self.stopped = False
        self.source_unsub = None
        self.source_entities = set()

    def _changed(self, site_id, records):
        self.hass.bus.async_fire(
            PRICE_REVISION_EVENT,
            {
                "api_version": 1,
                "producer_entry_id": self.entry.entry_id,
                "site_id": site_id,
                "revision": self.price_engine.revisions[site_id],
                "affected_slots": [r.start.isoformat() for r in records],
                "start": records[0].start.isoformat(),
                "end": records[-1].end.isoformat(),
            },
        )

    async def _audit_configuration(self):
        store = Store(self.hass, 1, f"{DOMAIN}.{self.entry.entry_id}.configuration")
        saved = await store.async_load() or {"current": None, "changes": []}
        previous = saved["current"]
        if saved["current"] != self.site:
            saved["changes"].append(
                {"at": dt_util.utcnow().isoformat(), "old": saved["current"], "new": self.site}
            )
            saved["current"] = self.site
            await store.async_save(saved)
        return previous

    async def start(self):
        await self.price_engine.async_load([self.site["id"]])
        await self.price_updater.tariffs.load()
        previous = await self._audit_configuration()
        if previous and previous != self.site:
            try:
                await self.reconfigure(previous, dt_util.utcnow())
            except ValueError, KeyError, TypeError:
                # Keep authoritative prior prices; startup re-verifies sources and
                # records precise missing/expired component errors per requested day.
                LOGGER.warning("Pricing configuration requires fresh verified source coverage")
        await self.schedule.startup()
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
        if self.site.get("price_entity"):
            self.source_entities.add(self.site["price_entity"])
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
            self.entry.async_create_task(
                self.hass, self.async_request_refresh(), "Publish provider readiness"
            )
        self._source_changed(None)

    async def reconfigure(self, previous, now):
        """Use stored raw spot inputs; select only affected, unstarted intervals."""
        if any(
            previous.get(k) != self.site.get(k)
            for k in (
                "nordpool_entry",
                "area",
                "timezone",
                "source_type",
                "price_entity",
                "price_unit",
                "price_basis",
            )
        ):
            return False  # A new source must first be verified by normal refresh.
        old_tariff, new_tariff = tariff_for(previous), tariff_for(self.site)
        before = {
            r.start: r.final_price_incl_vat
            for r in self.price_engine.records.get(self.site["id"], ())
        }

        def project(tariff, day, hour):
            return {
                **tariff,
                "components": [
                    r
                    for r in tariff["components"]
                    if r["valid_from"] <= day < r["valid_to"] and hour in active_hours(r)
                ],
            }

        def select(row):
            day = str(row.start.astimezone(ZoneInfo(self.site["timezone"])).date())
            hour = row.start.astimezone(ZoneInfo(self.site["timezone"])).hour
            tariff = project(new_tariff, day, hour)
            if tariff == project(old_tariff, day, hour) and self.site.get(
                "dso_mode"
            ) == previous.get("dso_mode"):
                return None
            locked_dso = any(r["id"] == "dso" and r.get("locked") for r in tariff["components"])
            if self.site.get("dso_mode") == "radius_c" and not locked_dso:
                key = RADIUS_GLN + ":" + RADIUS_CODE
                cached = self.price_updater.tariffs.cache.get(key, {})
                fetched = dt_util.parse_datetime(cached.get("fetched_at", ""))
                if (
                    not fetched
                    or (now - fetched).total_seconds() > self.site.get("dso_stale_days", 7) * 86400
                ):
                    if not self.site.get("dso_manual_fallback"):
                        raise ValueError("Verified DSO cache required for repricing")
                else:
                    tariff["grid_slots"], _ = normalize_tariffs(
                        cached["records"], RADIUS_GLN, RADIUS_CODE, row.start, row.end
                    )
            return tariff

        changed = await self.price_engine.async_reconfigure(self.site["id"], select, now)
        affected = tuple(
            r
            for r in self.price_engine.records.get(self.site["id"], ())
            if r.start >= now and before.get(r.start) != r.final_price_incl_vat
        )
        if affected:
            self._changed(self.site["id"], affected)
        return changed

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
        if report["status"] != "READY":
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self.entry.entry_id,
                is_fixable=True,
                data={"entry_id": self.entry.entry_id},
                severity=ir.IssueSeverity.WARNING,
                translation_key="pricing_not_ready",
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, self.entry.entry_id)
        return report
