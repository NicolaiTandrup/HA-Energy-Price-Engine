"""Stored current price and source readiness; state publication does not fetch."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import async_track_utc_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .device_diagnostics import COMPONENTS, availability, explanation, stored_breakdown
from .presentation import display_precision, display_value
from .status import day_result, quarter_result, source_status


def optional_estimate(unique_id):
    return "_estimated_price_" in unique_id or "_display_estimated_" in unique_id


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    from .localization import review_labels

    labels = await review_labels(hass)
    # HA's device page lists hidden entities too. Apply a one-time disabled default
    # for unused estimates, preserving registry/history and subsequent user opt-in.
    registry = er.async_get(hass)
    configured = bool(c.site.get("provisional_supplier"))
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id in {f"{c.site['id']}_readiness", f"{c.site['id']}_tomorrow_status"}:
            if entity.hidden_by is None:
                registry.async_update_entity(
                    entity.entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
                )
            continue
        if not optional_estimate(entity.unique_id):
            continue
        preferences = entity.options.get(DOMAIN, {})
        if not configured and preferences.get("provisional_configured") is not False:
            updates = {}
            if entity.hidden_by is None:
                updates["hidden_by"] = er.RegistryEntryHider.INTEGRATION
            if entity.disabled_by is None:
                updates["disabled_by"] = er.RegistryEntryDisabler.INTEGRATION
            if updates:
                registry.async_update_entity(entity.entity_id, **updates)
        elif configured:
            updates = {}
            if entity.hidden_by is er.RegistryEntryHider.INTEGRATION:
                updates["hidden_by"] = None
            if entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION:
                updates["disabled_by"] = None
            if updates:
                registry.async_update_entity(entity.entity_id, **updates)
        if preferences.get("provisional_configured") is not configured:
            registry.async_update_entity_options(
                entity.entity_id, DOMAIN, {**preferences, "provisional_configured": configured}
            )

    @callback
    def mark_new_defaults(event):
        if event.data.get("action") != "create":
            return
        entity = registry.async_get(event.data["entity_id"])
        if (
            entity
            and entity.config_entry_id == entry.entry_id
            and optional_estimate(entity.unique_id)
        ):
            registry.async_update_entity_options(
                entity.entity_id,
                DOMAIN,
                {**entity.options.get(DOMAIN, {}), "provisional_configured": configured},
            )

    entry.async_on_unload(
        hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, mark_new_defaults)
    )
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
            TomorrowReadinessSensor(c),
            AvailabilitySensor(c, "current", labels),
            AvailabilitySensor(c, "tomorrow", labels),
            AvailabilitySensor(c, "history", labels),
            ActivationSensor(c),
            BreakdownPeriodSensor(c),
            *[ComponentSensor(c, key) for key in COMPONENTS],
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
    _attr_entity_registry_enabled_default = False
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
    _attr_entity_registry_enabled_default = False
    _attr_device_class = "enum"
    _attr_options = ["READY", "INCOMPLETE", "STALE", "ERROR"]
    _attr_translation_key = "readiness"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_visible_default = False

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
    _attr_entity_registry_enabled_default = False
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
    _attr_entity_registry_enabled_default = False
    _attr_device_class = "enum"
    _attr_options = ["READY", "INCOMPLETE", "STALE", "ERROR"]
    _attr_translation_key = "tomorrow_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_visible_default = False

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_tomorrow_status"

    @property
    def native_value(self):
        return str(day_result(self.coordinator, 1).status)

    @property
    def extra_state_attributes(self):
        result = day_result(self.coordinator, 1)
        report = self.coordinator.schedule.days.get(self.site["id"], {}).get(
            str(
                dt_util.utcnow().astimezone(ZoneInfo(self.site["timezone"])).date()
                + timedelta(days=1)
            ),
            {},
        )
        return {
            "valid_slots": result.valid_slots,
            "expected_slots": result.expected_slots,
            "last_success": result.last_success,
            "reason": result.reason,
            "required_action": report.get("required_action"),
            "missing_components": report.get("missing_components", []),
            "affected_period": report.get("affected_period"),
            "next_scheduled_update": self.coordinator.schedule.next_update(
                dt_util.utcnow()
            ).isoformat(),
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
        if kind.startswith("estimated_"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = bool(self.site.get("provisional_supplier"))
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
            **({"api_version": 1} if self.kind == "current" else {}),
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
    _attr_entity_registry_enabled_default = False

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
    _attr_entity_registry_visible_default = True
    _attr_entity_registry_enabled_default = True
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
        self._attr_entity_registry_enabled_default = bool(self.site.get("provisional_supplier"))
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


class TomorrowReadinessSensor(TomorrowSensor):
    """Supported lowercase enum for UI; legacy uppercase identity stays intact.

    Hassfest requires lowercase translation keys, so the existing enum cannot be
    translated without changing its machine states. Keep it as hidden technical
    compatibility data and expose this small presentation counterpart instead.
    """

    _attr_options = ["ready", "incomplete", "stale", "error"]
    _attr_translation_key = "tomorrow_readiness"
    _attr_entity_registry_visible_default = True
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_tomorrow_readiness"

    @property
    def native_value(self):
        return super().native_value.lower()


class ComponentSensor(BaseSensor):
    """Fixed ore presentation of the actual stored ex-VAT component/VAT/final."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "øre/kWh"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, component):
        super().__init__(coordinator)
        self.component = component
        self._attr_unique_id = f"{self.site['id']}_component_{component}_ore"
        self._attr_translation_key = f"component_{component}"

    @property
    def native_value(self):
        return stored_breakdown(self.coordinator)["components"][self.component]

    @property
    def extra_state_attributes(self):
        data = stored_breakdown(self.coordinator)
        metadata = data["component_metadata"].get(self.component, {})
        return {
            **{k: v for k, v in data.items() if k not in {"components", "component_metadata"}},
            "verification": data["verification"]
            if data["components"][self.component] is not None
            else "missing",
            "applied_component": metadata,
            "vat_basis": "incl_vat"
            if self.component == "final"
            else "applied_vat_amount"
            if self.component == "vat"
            else "ex_vat",
            "subscriptions_included": False,
            "presentation_only": True,
            "canonical_unit": "DKK/kWh",
        }


class BreakdownPeriodSensor(BaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = "enum"
    _attr_options = ["current_quarter", "next_quarter", "unavailable"]
    _attr_translation_key = "breakdown_period"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_breakdown_period"

    @property
    def native_value(self):
        return stored_breakdown(self.coordinator)["period"]

    @property
    def extra_state_attributes(self):
        return {
            k: v
            for k, v in stored_breakdown(self.coordinator).items()
            if k not in {"components", "component_metadata", "source"}
        }


class AvailabilitySensor(BaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = "enum"
    _attr_options = [
        "ready",
        "loading",
        "waiting_first_quarter",
        "waiting_publication",
        "missing_components",
        "historical_gap",
        "verification_error",
        "storage_error",
        "stale",
        "missing_prices",
    ]

    def __init__(self, coordinator, scope, labels):
        super().__init__(coordinator)
        self.scope, self.labels = scope, labels
        self._attr_unique_id = f"{self.site['id']}_{scope}_availability"
        self._attr_translation_key = f"availability_{scope}"

    @property
    def native_value(self):
        return availability(self.coordinator, self.scope)["code"]

    @property
    def extra_state_attributes(self):
        facts = availability(self.coordinator, self.scope)
        return {**facts, "explanation": explanation(facts, self.labels)}


class ActivationSensor(BaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = "timestamp"
    _attr_translation_key = "prices_start_at"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.site['id']}_prices_start_at"
        self._attr_entity_registry_enabled_default = bool(self.site.get("pricing_start"))

    @property
    def native_value(self):
        return dt_util.parse_datetime(self.site.get("pricing_start", ""))
