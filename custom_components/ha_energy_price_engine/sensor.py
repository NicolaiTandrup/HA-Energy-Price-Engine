"""Nine native MVP sensors per site, with full precision and compact diagnostics."""

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import async_track_utc_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .status import availability, price, source_value, statistics

KINDS = (
    "current_spot",
    "current_final",
    "next_spot",
    "next_final",
    "average",
    "minimum",
    "maximum",
    "dso",
    "availability",
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([PriceSensor(entry.runtime_data, kind) for kind in KINDS])


class PriceSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, kind):
        super().__init__(coordinator)
        self.kind = kind
        self._attr_unique_id = f"{coordinator.site['id']}_{kind}"
        self._attr_translation_key = kind
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.site["id"])},
            name=coordinator.site["name"],
            manufacturer="Energy Price Engine",
            model="Electricity pricing",
            entry_type=DeviceEntryType.SERVICE,
            sw_version=coordinator.integration_version,
        )
        if kind == "availability":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        else:
            self._attr_native_unit_of_measurement = "øre/kWh"
            self._attr_suggested_display_precision = 2
            if kind in {"current_spot", "current_final", "dso"}:
                self._attr_state_class = SensorStateClass.MEASUREMENT

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        @callback
        def tick(_):
            self.async_write_ha_state()

        self.async_on_remove(async_track_utc_time_change(self.hass, tick, minute="*", second=0))

    @property
    def name(self):
        if (
            self.kind in {"average", "minimum", "maximum"}
            and statistics(self.coordinator)["scope"] == "remaining_day"
        ):
            da = self.coordinator.hass.config.language.startswith("da")
            return (
                {
                    "average": "Gennemsnit resten af dagen",
                    "minimum": "Minimum resten af dagen",
                    "maximum": "Maksimum resten af dagen",
                }
                if da
                else {
                    "average": "Remaining-day average",
                    "minimum": "Remaining-day minimum",
                    "maximum": "Remaining-day maximum",
                }
            )[self.kind]
        return super().name

    @property
    def native_value(self):
        if self.kind == "availability":
            facts = availability(self.coordinator)
            da = self.coordinator.hass.config.language.startswith("da")
            words = (
                {
                    "ready": "Klar",
                    "error": "Fejl — se årsag og afhjælpning",
                    "stale": "Forældet — kontroller kilden",
                    "waiting": "Priser fra {time}",
                    "missing": "Manglende priser — se kilde/tarif",
                }
                if da
                else {
                    "ready": "Ready",
                    "error": "Error — see reason and action",
                    "stale": "Stale — recheck source",
                    "waiting": "Prices available from {time}",
                    "missing": "Missing prices — inspect source/tariff",
                }
            )
            return words[facts["code"]].format(time=facts["available_from"] or "—")
        if self.kind in {"average", "minimum", "maximum"}:
            value = statistics(self.coordinator).get(self.kind)
        elif self.kind in {"current_final", "next_final"}:
            result = price(self.coordinator, int(self.kind == "next_final"))
            value = result.slots[0].price if result.slots else None
        else:
            value = source_value(self.coordinator, self.kind)
        return value * 100 if value is not None else None

    @property
    def extra_state_attributes(self):
        if self.kind == "availability":
            return {"site_id": self.coordinator.site["id"], **availability(self.coordinator)}
        if self.kind in {"average", "minimum", "maximum"}:
            return statistics(self.coordinator)
        return {
            "site_id": self.coordinator.site["id"],
            "vat_included": self.kind.endswith("final"),
            "canonical_unit": "DKK/kWh",
        }
