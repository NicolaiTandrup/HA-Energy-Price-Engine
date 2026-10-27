"""Native UI edits, invalid input, period selection and durable options/repricing."""

from copy import deepcopy
from datetime import UTC, date, datetime
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.configuration import (
    household_historical_example,
    validate_site,
)
from custom_components.ha_energy_price_engine.const import DOMAIN, PRICE_REVISION_EVENT
from custom_components.ha_energy_price_engine.price_engine import PriceEngine, day_bounds

from .test_integration import model, price_service, setup  # noqa: F401
from .wizard_helpers import options_advanced, save_options, source_page


@pytest.mark.usefixtures("price_service")
async def test_config_flow_site_unique_source_and_invalid_timezone(hass):
    source = MockConfigEntry(
        domain="nordpool", entry_id="np", data={}, state=config_entries.ConfigEntryState.LOADED
    )
    source.add_to_hass(hass)
    result = await source_page(hass, "Test home")
    fid = result["flow_id"]
    result = await hass.config_entries.flow.async_configure(fid, {"nordpool_entry": "np"})
    result = await hass.config_entries.flow.async_configure(
        fid, {"area": "DK2", "timezone": "invalid/timezone", "vat_percent": 25}
    )
    assert result["errors"] == {"timezone": "invalid_timezone"}
    result = await hass.config_entries.flow.async_configure(
        fid,
        {"area": "DK2", "timezone": "Europe/Copenhagen", "vat_percent": 25, "navigation": "review"},
    )
    with patch("custom_components.ha_energy_price_engine.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            fid, {"next_step_id": "wizard_save"}
        )
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["dated_components"] == []
    duplicate = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    duplicate = await hass.config_entries.flow.async_configure(
        duplicate["flow_id"], {"name": "Duplicate", "id": "test_home", "source_type": "nordpool"}
    )
    assert duplicate["errors"]["id"] == "duplicate_id"
    hass.config_entries.flow.async_abort(duplicate["flow_id"])
    source.mock_state(hass, config_entries.ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_options_edit_future_rate_reprice_once_and_survive_restart(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(
        domain="nordpool", entry_id="np", data={}, state=config_entries.ConfigEntryState.LOADED
    )
    source.add_to_hass(hass)
    entry = await setup(hass)
    c = entry.runtime_data
    before = c.price_engine.records["home"]
    events = []
    hass.bus.async_listen(PRICE_REVISION_EVENT, lambda event: events.append(event.data))
    options = await options_advanced(hass, entry.entry_id)
    assert options["type"] == FlowResultType.MENU
    assert "Saved settings" in options["description_placeholders"]["draft_status"]
    result = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "edit_rate"}
    )
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"rate": "0"})
    changed = {**model()["dated_components"][0], "amount": 33, "valid_from": "2026-10-24"}
    result = await hass.config_entries.options.async_configure(result["flow_id"], changed)
    assert result["type"] == FlowResultType.MENU
    # Staging changes does not mutate runtime or durable options.
    assert c.site["dated_components"][0]["amount"] == 11
    result = await save_options(hass, result["flow_id"])
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    c = entry.runtime_data
    assert entry.options["dated_components"][0]["amount"] == 33
    tomorrow = c.price_engine.lookup("home", *day_bounds(date(2026, 10, 24)))
    assert tomorrow[0].final_price_incl_vat == pytest.approx(
        before[-1].final_price_incl_vat + 0.22 * 1.25
    )
    assert all(
        c.price_engine.lookup("home", r.start, r.end)[0] == r
        for r in before
        if r.start < datetime(2026, 10, 23, 12, tzinfo=UTC)
    )
    # Reconfigure emits one future revision, identical verified source sync no second event.
    assert len(events) == 1 and len(events[0]["affected_slots"]) == 96
    restored = PriceEngine(hass, entry.entry_id)
    await restored.async_load(["home"])
    assert restored.lookup("home", *day_bounds(date(2026, 10, 24))) == tomorrow
    assert restored.audit["home"]  # Durable old/new row versions.
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "change",
    [
        {"amount": -1},
        {"amount": float("nan")},
        {"vat_rate": 1.1},
        {"unit": "unknown"},
        {"vat_included": "false"},
        {"source": ""},
        {"valid_to": "2025-01-01"},
        {"valid_from": "not-a-date"},
        {"id": "unknown"},
        {"unit": "DKK/month"},
        {"eligibility": "unverified"},
    ],
)
def test_invalid_business_inputs_rejected(change):
    site = model()
    site["dated_components"][0].update(change)
    with pytest.raises((ValueError, TypeError)):
        validate_site(site)


def test_overlap_and_bounded_ewii_example():
    site = model()
    site["dated_components"].append(deepcopy(site["dated_components"][0]))
    with pytest.raises(ValueError, match="Overlapping"):
        validate_site(site)
    rate = household_historical_example()
    assert rate["amount"] == 0.030 and rate["vat_included"] is False
    assert (rate["valid_from"], rate["valid_to"]) == ("2026-06-01", "2026-10-01")
    assert not any(r["amount"] == 0.030 for r in model("summer_house")["dated_components"])


@pytest.mark.usefixtures("price_service")
async def test_options_add_overlap_remove_dso_tax_and_discard(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(
        domain="nordpool", entry_id="np", data={}, state=config_entries.ConfigEntryState.LOADED
    )
    source.add_to_hass(hass)
    entry = await setup(hass)
    original = deepcopy(dict(entry.data))
    result = await options_advanced(hass, entry.entry_id)
    fid = result["flow_id"]
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "add_rate"})
    # The form itself validates invalid overlaps, not only the pure helper.
    result = await hass.config_entries.options.async_configure(fid, original["dated_components"][0])
    assert result["errors"]["base"] == "invalid_configuration"
    subscription = {
        **original["dated_components"][0],
        "id": "subscription",
        "unit": "DKK/month",
        "amount": 50,
    }
    result = await hass.config_entries.options.async_configure(fid, subscription)
    assert result["type"] == FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(fid, {"next_step_id": "wizard_grid"})
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        fid,
        {
            "dso_mode": "manual",
            "dso_manual_fallback": True,
            "dso_stale_days": 3,
            "navigation": "review",
        },
    )
    assert result["type"] == FlowResultType.MENU
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "advanced"})
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "wizard_charges"})
    result = await hass.config_entries.options.async_configure(
        fid,
        {
            "danish_public_rates": True,
            "heating_registered": True,
            "annual_usage_kwh": 4500,
            "usage_year": 2026,
            "navigation": "review",
        },
    )
    assert result["type"] == FlowResultType.MENU
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "advanced"})
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "remove_rate"})
    result = await hass.config_entries.options.async_configure(fid, {"rate": "2"})
    assert result["type"] == FlowResultType.MENU
    # Abort before Save: no runtime or durable mutation from any staged form.
    hass.config_entries.options.async_abort(fid)
    assert not entry.options and entry.data == original
    assert entry.runtime_data.site == original
    assert await hass.config_entries.async_unload(entry.entry_id)
