"""Fixed monetary presentation without changing stored values or Recorder identities."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.ha_energy_price_engine import apply_settings
from custom_components.ha_energy_price_engine.charging_diagnostics import charging_breakdown
from custom_components.ha_energy_price_engine.component_status import review
from custom_components.ha_energy_price_engine.configuration import settings
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.presentation import format_price
from custom_components.ha_energy_price_engine.sensor import (
    DisplaySensor,
    PriceSensor,
    RawSpotSensor,
)

from .test_integration import price_service, setup  # noqa: F401


@pytest.mark.parametrize(
    "value,ore,dkk",
    [
        (0, "0.00", "0.0000"),
        (1.9081175, "190.81", "1.9081"),
        (-0.123456, "-12.35", "-0.1235"),
        (0.00005, "0.01", "0.0001"),
        (-0.0000001, "0.00", "0.0000"),
        (None, "—", "—"),
    ],
)
@pytest.mark.parametrize("separator", [".", ","])
def test_fixed_price_text_and_locale(value, ore, dkk, separator):
    assert format_price(value, "øre/kWh", separator) == ore.replace(".", separator)
    assert format_price(value, "DKK/kWh", separator) == dkk.replace(".", separator)


@pytest.mark.usefixtures("price_service")
async def test_all_presentation_entities_and_canonical_registry_survive_unit_changes(hass, freezer):
    freezer.move_to("2026-10-27T12:00:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    registry = er.async_get(hass)
    canonical_id = registry.async_get_entity_id("sensor", DOMAIN, "home_current_price")
    old_rows = c.price_engine.records["home"]
    price = PriceSensor(c).native_value
    assert price == pytest.approx(0.41625)
    for unit, precision in [("øre/kWh", 2), ("DKK/kWh", 4), ("øre/kWh", 2)]:
        assert await apply_settings(hass, entry, {**settings(entry), "display_unit": unit})
        await hass.async_block_till_done()
        c = entry.runtime_data
        assert c.price_engine.records["home"] == old_rows
        assert registry.async_get_entity_id("sensor", DOMAIN, "home_current_price") == canonical_id
        canonical = hass.states.get(canonical_id)
        assert canonical.attributes["unit_of_measurement"] == "DKK/kWh"
        assert canonical.attributes["state_class"] == "measurement"
        assert canonical.attributes["canonical_technical_value"] is True
        assert float(canonical.state) == price
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
        ):
            sensor = DisplaySensor(c, kind)
            assert sensor.suggested_display_precision == precision and sensor.state_class is None
            assert sensor.native_unit_of_measurement == unit
            eid = registry.async_get_entity_id("sensor", DOMAIN, sensor.unique_id)
            assert (
                registry.async_get(eid).options["sensor"]["suggested_display_precision"]
                == precision
            )
        assert DisplaySensor(c, "current").native_value == price * (100 if unit == "øre/kWh" else 1)
        assert DisplaySensor(c, "raw_current").native_value == RawSpotSensor(c).native_value * (
            100 if unit == "øre/kWh" else 1
        )
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("language,separator", [("en", "."), ("en-GB", "."), ("da", ",")])
@pytest.mark.parametrize("unit,expected", [("øre/kWh", "41.63"), ("DKK/kWh", "0.4163")])
@pytest.mark.usefixtures("price_service")
async def test_review_diagnostics_and_technical_picker_follow_one_unit(
    hass, freezer, language, separator, unit, expected
):
    from .wizard_helpers import options_advanced

    freezer.move_to("2026-10-27T12:00:00Z")
    hass.config.language = language
    entry = await setup(hass)
    await apply_settings(hass, entry, {**settings(entry), "display_unit": unit})
    before = entry.runtime_data.price_engine.records["home"]
    with patch(
        "custom_components.ha_energy_price_engine.price_engine.calculate",
        side_effect=AssertionError("display recomposed"),
    ):
        summary, _ = await review(hass, entry)
        assert expected.replace(".", separator) + " " + unit in summary["rows"]["setup_final"]
        text = await charging_breakdown(hass, entry, datetime(2026, 10, 27, 12, tzinfo=UTC))
        assert expected.replace(".", separator) + " " + unit in text
        assert "afrundes" in text if language == "da" else "Rounded for display only" in text
        assert ("øre/kWh" not in text) if unit == "DKK/kWh" else ("DKK/kWh" not in text)
        result = await options_advanced(hass, entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "storage_tools"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "breakdown"}
        )
        labels = [
            o["label"] for f in result["data_schema"].schema.values() for o in f.config["options"]
        ]
        assert all(unit in label and expected.replace(".", separator) in label for label in labels)
        hass.config_entries.options.async_abort(result["flow_id"])
    assert entry.runtime_data.price_engine.records["home"] == before
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "language,mode,separator",
    [("en", "decimal_comma", ","), ("da", "comma_decimal", "."), ("en-GB", "quote_decimal", ".")],
)
async def test_native_user_number_format_overrides_language(hass, language, mode, separator):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from custom_components.ha_energy_price_engine.localization import review_labels

    request = {"hass_user": SimpleNamespace(id="fictional-qa-user")}
    store = SimpleNamespace(data={"language": {"language": language, "number_format": mode}})
    with (
        patch("custom_components.ha_energy_price_engine.localization.current_request") as context,
        patch(
            "custom_components.ha_energy_price_engine.localization.async_user_store",
            AsyncMock(return_value=store),
        ),
    ):
        context.get.return_value = request
        assert (await review_labels(hass))["decimal_separator"] == separator
