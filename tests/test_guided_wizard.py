"""User-visible native wizard, durable drafts, atomic apply and presentation invariants."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.sensor import DisplaySensor, PriceSensor

from .test_integration import model, price_service, setup  # noqa: F401
from .wizard_helpers import options_review, source_page


@pytest.mark.usefixtures("price_service")
async def test_new_official_wizard_source_defaults_review_save_incomplete(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(
        domain="nordpool",
        title="Official DK2",
        data={"areas": ["DK2"]},
        state=ConfigEntryState.LOADED,
    )
    source.add_to_hass(hass)
    r = await source_page(hass, "Sommerhus")
    fields = {str(k) for k in r["data_schema"].schema}
    assert fields == {"nordpool_entry", "navigation"}
    assert not fields & {"price_entity", "price_unit", "price_basis", "stale_minutes"}
    fid = r["flow_id"]
    r = await hass.config_entries.flow.async_configure(fid, {"nordpool_entry": source.entry_id})
    defaults = {str(k): k.default() for k in r["data_schema"].schema if callable(k.default)}
    assert defaults["area"] == "DK2" and defaults["timezone"] == "Europe/Copenhagen"
    assert defaults["vat_percent"] == 25
    r = await hass.config_entries.flow.async_configure(
        fid, {"area": "DK2", "timezone": "Europe/Copenhagen", "vat_percent": 25}
    )
    assert r["step_id"] == "wizard_grid"
    r = await hass.config_entries.flow.async_configure(
        fid, {"dso_mode": "manual", "navigation": "next"}
    )
    r = await hass.config_entries.flow.async_configure(
        fid, {"supplier": "ewii", "add_contract": False}
    )
    r = await hass.config_entries.flow.async_configure(fid, {"danish_public_rates": False})
    r = await hass.config_entries.flow.async_configure(fid, {"display_unit": "øre/kWh"})
    assert r["step_id"] == "wizard_review"
    assert r["menu_options"][0] == "wizard_save"
    assert "supplier" in r["description_placeholders"]["review"]
    created = await hass.config_entries.flow.async_configure(fid, {"next_step_id": "wizard_save"})
    await hass.async_block_till_done()
    entry = created["result"]
    assert entry.unique_id == "sommerhus" and entry.version == 3
    assert entry.data["price_unit"] == "DKK/MWh" and entry.data["vat"] == 0.25
    assert entry.data["dated_components"] == []  # EWII label did not manufacture a rate.
    assert entry.runtime_data.data["status"] != "READY"
    assert "supplier" in entry.runtime_data.data["missing_components"]
    assert "2026-10-23" in entry.runtime_data.data["reason"]
    assert "Configure" in entry.runtime_data.data["required_action"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_interrupted_options_resume_back_discard_does_not_apply(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(
        domain="nordpool", entry_id="np", data={"areas": ["DK2"]}, state=ConfigEntryState.LOADED
    )
    source.add_to_hass(hass)
    entry = await setup(hass)
    before = deepcopy(dict(entry.options))
    rows = entry.runtime_data.price_engine.records["home"]
    r = await hass.config_entries.options.async_init(entry.entry_id)
    fid = r["flow_id"]
    r = await hass.config_entries.options.async_configure(
        fid, {"name": "Changed draft name", "source_type": "nordpool"}
    )
    assert r["step_id"] == "wizard_source"
    hass.config_entries.options.async_abort(fid)
    saved = await Store(hass, 1, f"{DOMAIN}.wizard.{entry.entry_id}").async_load()
    assert saved["draft"]["name"] == "Changed draft name"
    assert dict(entry.options) == before and entry.runtime_data.price_engine.records["home"] == rows
    r = await hass.config_entries.options.async_init(entry.entry_id)
    assert r["step_id"] == "wizard_source"
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"navigation": "back"})
    assert r["step_id"] == "wizard_site"
    r = await hass.config_entries.options.async_configure(
        r["flow_id"],
        {"name": "Changed draft name", "source_type": "nordpool", "navigation": "review"},
    )
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "wizard_discard"}
    )
    assert r["step_id"] == "wizard_discard"
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"confirm": True})
    assert r["reason"] == "draft_discarded"
    assert not await Store(hass, 1, f"{DOMAIN}.wizard.{entry.entry_id}").async_load()
    assert dict(entry.options) == before
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_beta1_migration_version_display_and_immutable_api(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(domain="nordpool", entry_id="np", state=ConfigEntryState.LOADED)
    source.add_to_hass(hass)
    entry = await setup(hass)
    c = entry.runtime_data
    assert entry.version == 3
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]
    assert device.sw_version == "0.1.0-beta.1"  # Installed manifest, not flow/core version.
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    original = c.price_engine.records["home"]
    price = PriceSensor(c).native_value
    display = DisplaySensor(c, "current")
    assert display.native_value == pytest.approx(price * 100)
    assert display.native_unit_of_measurement == "øre/kWh"
    assert display.state_class is None  # Display preferences never reinterpret statistics.
    uid = display.unique_id
    r = await options_review(hass, entry.entry_id)
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "wizard_display"}
    )
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"display_unit": "DKK/kWh"})
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "wizard_save"}
    )
    await hass.async_block_till_done()
    c = entry.runtime_data
    assert c.price_engine.records["home"] == original
    assert PriceSensor(c).native_value == price
    assert DisplaySensor(c, "current").native_value == price
    assert DisplaySensor(c, "current").unique_id != uid
    assert (
        get_api(hass).lookup("home", original[0].start, original[-1].end, now=now).records
        == original
    )
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)
