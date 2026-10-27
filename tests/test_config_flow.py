"""Native UI edits, invalid input, period selection and durable options/repricing."""

from copy import deepcopy
from datetime import UTC, date, datetime

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
from .wizard_helpers import options_rates, save_options, source_page


@pytest.mark.usefixtures("price_service")
async def test_config_flow_unique_site_names_and_verified_source_defaults(hass):
    source = MockConfigEntry(
        domain="nordpool",
        entry_id="np",
        data={"areas": ["DK2"]},
        state=config_entries.ConfigEntryState.LOADED,
    )
    source.add_to_hass(hass)
    first = await source_page(hass, "Test home")
    hass.config_entries.flow.async_abort(first["flow_id"])
    second = await source_page(hass, "Test home")
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len({e.unique_id for e in entries}) == 2
    assert all(e.data["timezone"] == "Europe/Copenhagen" and e.data["vat"] == 0.25 for e in entries)
    hass.config_entries.flow.async_abort(second["flow_id"])
    for e in entries:
        assert await hass.config_entries.async_unload(e.entry_id)
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
    options = await options_rates(hass, entry.entry_id)
    assert options["type"] == FlowResultType.MENU
    assert options["step_id"] == "rates"
    result = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "edit_rate"}
    )
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"rate": "0"})
    changed = {**model()["dated_components"][0], "amount": 33, "valid_from": "2026-10-24"}
    result = await hass.config_entries.options.async_configure(result["flow_id"], changed)
    assert result["type"] == FlowResultType.MENU
    # The accepted edit immediately updates options and runtime.
    assert any(
        x["id"] == "supplier" and x["amount"] == 33 for x in entry.options["dated_components"]
    )
    result = await save_options(hass, result["flow_id"])
    assert result["step_id"] == "setup_review"
    await hass.async_block_till_done()
    c = entry.runtime_data
    assert (
        next(r for r in entry.options["dated_components"] if r["id"] == "supplier")["amount"] == 33
    )
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
    result = await options_rates(hass, entry.entry_id)
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
    assert result["step_id"] == "rates"
    assert any(r["id"] == "subscription" for r in entry.options["dated_components"])
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "remove_rate"})
    index = next(
        i for i, r in enumerate(entry.options["dated_components"]) if r["id"] == "subscription"
    )
    result = await hass.config_entries.options.async_configure(fid, {"rate": str(index)})
    assert result["step_id"] == "rates"
    hass.config_entries.options.async_abort(fid)
    assert not any(r["id"] == "subscription" for r in entry.options["dated_components"])
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, config_entries.ConfigEntryState.NOT_LOADED)
