"""Stored current price and source readiness; state publication does not fetch."""

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import async_track_utc_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .presentation import display_precision, display_value
from .status import day_result, quarter_result, source_status


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities(
        [
            PriceSensor(c),
            EstimatedPriceSensor(c),
            EstimatedPriceSensor(c, 1),
            RawSpotSensor(c),
            RawSpotSensor(c, 1),
            RawReadinessSensor(c),
            RawReadinessSensor(c, 1),
            FinalStatusSensor(c),
            NextReadinessSensor(c),
            HistoricalCoverageSensor(c),
            PricingProblemSensor(c),
            ReadinessSensor(c),
            NextPriceSensor(c),
            *[DayStatisticSensor(c, kind) for kind in ("minimum", "maximum", "average")],
            TomorrowSensor(c),
            *[
                DisplaySensor(c, kind)
                for kind in (
                    "current",
                    "next",
                    "minimum",
                    "maximum",
                    "average",
                    "raw_current",
                    "raw_next",
                    "estimated_current",
                    "estimated_next",
                )
            ],
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
            model="Electricity pricing software",
            entry_type=DeviceEntryType.SERVICE,
            sw_version=getattr(coordinator, "integration_version", None),
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        @callback
        def publish(_):
            self.async_write_ha_state()

        self.async_on_remove(async_track_utc_time_change(self.hass, publish, minute="*", second=0))

    def current_result(self, offset=0):
        return quarter_result(self.coordinator, offset)


class PriceSensor(BaseSensor):
    _attr_translation_key = "current_price"
    _attr_native_unit_of_measurement = "DKK/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 4
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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
            "canonical_technical_value": True,
            "api_version": 1,
            "site_id": self.site["id"],
            "readiness": str(self.current_result().status),
            "revision": self.coordinator.price_engine.revisions.get(self.site["id"], 0),
            "vat_included": True,
        }


class ReadinessSensor(BaseSensor):
    _attr_device_class = "enum"
    _attr_options = ["READY", "INCOMPLETE", "STALE", "ERROR"]
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
    _attr_suggested_display_precision = 4
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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
    _attr_device_class = "enum"
    _attr_options = ["READY", "INCOMPLETE", "STALE", "ERROR"]
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


class DisplaySensor(BaseSensor):
    """Unit-specific presentation identity: canonical sensors/statistics never change."""

    _attr_suggested_display_precision = 4

    def __init__(self, coordinator, kind):
        super().__init__(coordinator)
        self.kind = kind
        self.unit = self.site.get("display_unit", "øre/kWh")
        self._attr_native_unit_of_measurement = self.unit
        self._attr_suggested_display_precision = display_precision(self.unit)
        suffix = "ore" if self.unit == "øre/kWh" else "dkk"
        self._attr_unique_id = f"{self.site['id']}_display_{kind}_{suffix}"
        self._attr_translation_key = f"display_{kind}"
        if kind.startswith("raw_"):
            basis = "incl_vat" if self.site.get("price_basis") == "spot_incl_vat" else "ex_vat"
            self._attr_translation_key += "_" + basis

    @property
    def native_value(self):
        if self.kind in {"raw_current", "raw_next"}:
            value = RawSpotSensor(self.coordinator, int(self.kind == "raw_next")).native_value
        elif self.kind in {"estimated_current", "estimated_next"}:
            value = EstimatedPriceSensor(
                self.coordinator, int(self.kind == "estimated_next")
            ).native_value
        elif self.kind in {"current", "next"}:
            result = self.current_result(1 if self.kind == "next" else 0)
            value = (
                result.records[0].final_price_incl_vat
                if str(result.status) == "READY" and result.records
                else None
            )
        else:
            value = DayStatisticSensor(self.coordinator, self.kind).native_value
        return display_value(value, self.unit)

    @property
    def extra_state_attributes(self):
        return {
            "site_id": self.site["id"],
            "stored_and_api_unit": "DKK/kWh",
            "vat_included": self.site.get("price_basis") == "spot_incl_vat"
            if self.kind.startswith("raw_")
            else True,
            "verification": "ESTIMATED_UNVERIFIED"
            if self.kind.startswith("estimated_")
            else RawReadinessSensor(self.coordinator, int(self.kind == "raw_next")).native_value
            if self.kind.startswith("raw_")
            else "verified_only",
            "eligible_for_control": False,
            "presentation_only": True,
        }


class RawSpotSensor(BaseSensor):
    """Verified spot source, independent of final composition and ledger success."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    _attr_native_unit_of_measurement = "DKK/kWh"
    _attr_suggested_display_precision = 4

    def __init__(self, coordinator, offset=0):
        super().__init__(coordinator)
        self.offset = offset
        self._attr_unique_id = f"{self.site['id']}_raw_spot_{offset}"
        self._attr_translation_key = "raw_current" if offset == 0 else "raw_next"

    @property
    def native_value(self):
        now = dt_util.utcnow()
        start = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0) + timedelta(
            minutes=15 * self.offset
        )
        updater = self.coordinator.price_updater
        for day, slots in updater.raw_slots.items():
            report = updater.raw_reports[day]
            verified = dt_util.parse_datetime(report.get("verified_at", ""))
            if (
                report.get("price_basis") == "all_in"
                or report["status"] == "ERROR"
                or not verified
                or not 0 <= (now - verified).total_seconds() < 7200
            ):
                continue
            for slot in slots:
                if slot.start == start:
                    return slot.price
        return None

    @property
    def extra_state_attributes(self):
        return {
            "canonical_technical_value": True,
            "price_basis": self.site.get("price_basis"),
            "currency": "DKK",
            "final_price": False,
            "vat_included": self.site.get("price_basis") == "spot_incl_vat",
        }


class RawReadinessSensor(BaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = "enum"
    _attr_options = ["ready", "incomplete", "stale", "error"]

    def __init__(self, coordinator, offset=0):
        super().__init__(coordinator)
        self.offset = offset
        self._attr_unique_id = f"{self.site['id']}_raw_readiness_{offset}"
        self._attr_translation_key = "raw_today" if offset == 0 else "raw_tomorrow"

    @property
    def report(self):
        from zoneinfo import ZoneInfo

        day = dt_util.utcnow().astimezone(ZoneInfo(self.site["timezone"])).date() + timedelta(
            days=self.offset
        )
        return self.coordinator.price_updater.raw_reports.get(str(day), {})

    @property
    def native_value(self):
        report = self.report
        verified = dt_util.parse_datetime(report.get("verified_at", ""))
        if (
            report.get("status") == "READY"
            and verified
            and (dt_util.utcnow() - verified).total_seconds() >= 7200
        ):
            return "stale"
        return report.get("status", "INCOMPLETE").lower()

    @property
    def extra_state_attributes(self):
        return self.report


class PricingProblemSensor(BaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = "enum"
    _attr_options = [
        "none",
        "source",
        "grid",
        "storage",
        "composition",
        "configuration",
        "activation",
        "supplier",
        "electricity_tax",
        "energinet_net",
        "energinet_system",
        "dso",
    ]
    _attr_translation_key = "pricing_problem"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_pricing_problem"

    @property
    def report(self):
        from zoneinfo import ZoneInfo

        activation = dt_util.parse_datetime(self.site.get("pricing_start", ""))
        if activation and activation > dt_util.utcnow():
            day = str(activation.astimezone(ZoneInfo(self.site["timezone"])).date())
            return self.coordinator.schedule.days.get(self.site["id"], {}).get(
                day, self.coordinator.data or {}
            )
        return self.coordinator.data or {}

    @property
    def native_value(self):
        activation = dt_util.parse_datetime(self.site.get("pricing_start", ""))
        report = self.report
        if activation and activation > dt_util.utcnow() and report.get("status") == "READY":
            return "activation"
        missing = report.get("missing_components", [])
        return next(
            (
                k
                for k in ("supplier", "dso", "energinet_net", "energinet_system", "electricity_tax")
                if k in missing
            ),
            report.get("failure_stage") or "none",
        )

    @property
    def extra_state_attributes(self):
        report = self.report
        return {
            "prices_start_at": self.site.get("pricing_start"),
            **{
                k: report.get(k)
                for k in (
                    "affected_period",
                    "missing_components",
                    "reason",
                    "required_action",
                    "failure_stage",
                )
            },
        }


class FinalStatusSensor(ReadinessSensor):
    """Localized enum alongside preserved legacy uppercase status/API contracts."""

    _attr_options = ["ready", "incomplete", "stale", "error"]
    _attr_translation_key = "final_status"
    _readiness_scope = "current_quarter"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_final_status"

    @property
    def native_value(self):
        return str(self.current_result().status).lower()

    @property
    def extra_state_attributes(self):
        result = self.current_result()
        return {
            **source_status(self.coordinator),
            "health": str(result.status),
            "health_scope": self._readiness_scope,
            "last_error": result.reason,
        }


class EstimatedPriceSensor(BaseSensor):
    """Unverified visualization only; not a producer API or control input."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    _attr_native_unit_of_measurement = "DKK/kWh"
    _attr_suggested_display_precision = 4

    def __init__(self, coordinator, offset=0):
        super().__init__(coordinator)
        self.offset = offset
        self._attr_unique_id = f"{self.site['id']}_estimated_price_{offset}"
        self._attr_translation_key = "estimated_current" if offset == 0 else "estimated_next"

    @property
    def native_value(self):
        now = dt_util.utcnow()
        target = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0) + timedelta(
            minutes=15 * self.offset
        )
        for day, rows in self.coordinator.price_updater.estimated_slots.items():
            raw = self.coordinator.price_updater.raw_reports.get(day, {})
            verified = dt_util.parse_datetime(raw.get("verified_at", ""))
            if (
                raw.get("status") != "READY"
                or not verified
                or not 0 <= (now - verified).total_seconds() < 7200
            ):
                continue
            for row in rows:
                if row.start == target:
                    return row.price
        return None

    @property
    def extra_state_attributes(self):
        return {
            "canonical_technical_value": True,
            "verification": "ESTIMATED_UNVERIFIED",
            "visualization_only": True,
            "eligible_for_control": False,
            "authoritative_api": False,
            "vat_included": True,
        }


class NextReadinessSensor(FinalStatusSensor):
    _readiness_scope = "next_quarter"
    _attr_translation_key = "next_quarter_status"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_next_quarter_status"

    def current_result(self, offset=1):
        return super().current_result(offset)


class HistoricalCoverageSensor(FinalStatusSensor):
    _readiness_scope = "historical_full_day"
    _attr_translation_key = "historical_day_status"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_historical_day_status"

    def current_result(self, offset=0):
        return day_result(self.coordinator)
