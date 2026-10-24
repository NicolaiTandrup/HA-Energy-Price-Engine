"""Stored current price and source readiness; state publication does not fetch."""

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import async_track_utc_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([PriceSensor(entry.runtime_data), ReadinessSensor(entry.runtime_data)])


class BaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.site = coordinator.site
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.site["id"])},
            name=self.site["name"],
            manufacturer="Energy Price Engine",
        )


class PriceSensor(BaseSensor):
    _attr_translation_key = "current_price"
    _attr_native_unit_of_measurement = "DKK/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_current_price"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        @callback
        def publish(_):
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_utc_time_change(self.hass, publish, minute=[0, 15, 30, 45], second=0)
        )

    @property
    def native_value(self):
        now = dt_util.utcnow()
        rows = self.coordinator.price_engine.lookup(
            self.site["id"], now, now + timedelta(microseconds=1)
        )
        return rows[0].final_price_incl_vat if rows else None

    @property
    def extra_state_attributes(self):
        return {
            "api_version": 1,
            "site_id": self.site["id"],
            "readiness": (self.coordinator.data or {}).get("status", "INCOMPLETE"),
            "revision": self.coordinator.price_engine.revisions.get(self.site["id"], 0),
            "vat_included": True,
        }


class ReadinessSensor(BaseSensor):
    _attr_translation_key = "readiness"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_readiness"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("status", "INCOMPLETE")

    @property
    def extra_state_attributes(self):
        return {k: v for k, v in (self.coordinator.data or {}).items() if k != "status"}
