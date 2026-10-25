"""Native summaries stay complete, source-bound and read-only across day boundaries."""

from datetime import UTC, date, datetime
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import selector
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.sensor import (
    DayStatisticSensor,
    NextPriceSensor,
    TomorrowSensor,
)
from custom_components.ha_energy_price_engine.sources import async_source_defaults
from custom_components.ha_energy_price_engine.status import slot_breakdown, source_status

from .test_integration import model, price_service, setup  # noqa: F401
from .test_price_engine import rows


@pytest.mark.usefixtures("price_service")
async def test_opaque_entry_selection_replacement_and_readable_status(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    first = MockConfigEntry(
        domain="nordpool",
        title="Official DK2 household",
        entry_id="01K8OPAQUE_SOURCE_A",
        data={"areas": ["DK2"]},
        state=ConfigEntryState.LOADED,
    )
    first.add_to_hass(hass)
    assert (await async_source_defaults(hass))["nordpool_entry"] == first.entry_id
    form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    field = next(v for k, v in form["data_schema"].schema.items() if str(k) == "nordpool_entry")
    assert isinstance(field, selector.ConfigEntrySelector)
    assert (
        field.config["integration"] == "nordpool"
    )  # HA renders actual entry titles, not text IDs.
    hass.config_entries.flow.async_abort(form["flow_id"])
    entry = await setup(hass, {**model(), "nordpool_entry": first.entry_id})
    assert source_status(entry.runtime_data)["source"] == first.title
    second = MockConfigEntry(
        domain="nordpool",
        title="Replacement official source",
        entry_id="01K8OPAQUE_SOURCE_B",
        data={"areas": ["DK2"]},
        state=ConfigEntryState.LOADED,
    )
    second.add_to_hass(hass)
    assert await async_source_defaults(hass) == {}
    options = await hass.config_entries.options.async_init(entry.entry_id)
    options = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "site"}
    )
    options = await hass.config_entries.options.async_configure(
        options["flow_id"], {"name": "House", "nordpool_entry": second.entry_id}
    )
    saved = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "save"}
    )
    assert saved["type"] == "create_entry"
    await hass.async_block_till_done()
    assert entry.options["nordpool_entry"] == second.entry_id
    assert entry.runtime_data.site["id"] == "home"
    assert source_status(entry.runtime_data)["source"] == second.title
    assert await hass.config_entries.async_unload(entry.entry_id)
    first.mock_state(hass, ConfigEntryState.NOT_LOADED)
    second.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_daily_stats_next_price_and_selected_breakdown_do_not_fetch(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    with patch.object(c.price_updater, "refresh", side_effect=AssertionError("read fetched")):
        assert NextPriceSensor(c).native_value is not None
        for kind in ("minimum", "maximum", "average"):
            assert DayStatisticSensor(c, kind).native_value == pytest.approx(0.41625)
        assert TomorrowSensor(c).native_value == "READY"
        assert TomorrowSensor(c).extra_state_attributes["expected_slots"] == 96
        status = source_status(c)
        assert status["resolution_minutes"] == 15 and status["currency"] == "DKK"
        assert status["next_scheduled_update"].endswith("23:59:00+02:00")
        options = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            options["flow_id"], {"next_step_id": "breakdown"}
        )
        instant = rows(date(2026, 10, 23))[0].start
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"slot": instant.isoformat()}
        )
        text = result["description_placeholders"]["slot_breakdown"]
        assert "supplier:" in text and "Stored final:" in text and "electricity_tax:" in text
        assert "revision:" in text
        hass.config_entries.options.async_abort(result["flow_id"])
        c.schedule.days["home"]["2026-10-23"]["status"] = "INCOMPLETE"
        assert DayStatisticSensor(c, "minimum").native_value is None
        c.schedule.days["home"]["2026-10-24"]["status"] = "STALE"
        assert TomorrowSensor(c).native_value == "STALE"
        assert "No stored price" in slot_breakdown(c, datetime(2026, 10, 28, tzinfo=UTC))
    assert await hass.config_entries.async_unload(entry.entry_id)
