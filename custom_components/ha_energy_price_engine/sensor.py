"""Stored current price and source readiness; state publication does not fetch."""

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import async_track_utc_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import ConsumerAPI
from .const import DOMAIN
from .status import day_result, source_status


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities(
        [
            PriceSensor(c),
            ReadinessSensor(c),
            NextPriceSensor(c),
            *[DayStatisticSensor(c, kind) for kind in ("minimum", "maximum", "average")],
            TomorrowSensor(c),
        ]
    )


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

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        @callback
        def publish(_):
            self.async_write_ha_state()

        self.async_on_remove(async_track_utc_time_change(self.hass, publish, minute="*", second=0))

    def current_result(self, offset=0):
        now = dt_util.utcnow()
        start = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0) + timedelta(
            minutes=15 * offset
        )
        return ConsumerAPI(self.coordinator.hass).lookup(
            self.site["id"],
            start,
            start + timedelta(minutes=15),
            now=now,
            producer_entry_id=self.coordinator.entry.entry_id,
        )


class PriceSensor(BaseSensor):
    _attr_translation_key = "current_price"
    _attr_native_unit_of_measurement = "DKK/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_current_price"

    @property
    def native_value(self):
        result = self.current_result()
        return (
            result.records[0].final_price_incl_vat
            if str(result.status) == "READY" and result.records
            else None
        )

    @property
    def extra_state_attributes(self):
        return {
            "api_version": 1,
            "site_id": self.site["id"],
            "readiness": str(self.current_result().status),
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
        return str(self.current_result().status)

    @property
    def extra_state_attributes(self):
        return source_status(self.coordinator)


class NextPriceSensor(PriceSensor):
    _attr_translation_key = "next_price"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_next_price"

    def current_result(self, offset=1):
        return super().current_result(offset)


class DayStatisticSensor(BaseSensor):
    _attr_native_unit_of_measurement = "DKK/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, kind):
        super().__init__(coordinator)
        self.kind = kind
        self._attr_translation_key = f"today_{kind}"
        self._attr_unique_id = f"{self.site['id']}_today_{kind}"

    @property
    def native_value(self):
        result = day_result(self.coordinator)
        if str(result.status) != "READY" or not result.records:
            return None
        values = [r.final_price_incl_vat for r in result.records]
        return {"minimum": min, "maximum": max, "average": lambda v: sum(v) / len(v)}[self.kind](
            values
        )


class TomorrowSensor(BaseSensor):
    _attr_translation_key = "tomorrow_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_tomorrow_status"

    @property
    def native_value(self):
        return str(day_result(self.coordinator, 1).status)

    @property
    def extra_state_attributes(self):
        result = day_result(self.coordinator, 1)
        return {
            "valid_slots": result.valid_slots,
            "expected_slots": result.expected_slots,
            "last_success": result.last_success,
            "reason": result.reason,
        }
