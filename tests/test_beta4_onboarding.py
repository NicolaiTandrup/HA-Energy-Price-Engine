"""Direct supplier questions, explicit approval and actual persisted completion."""

import pytest
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.configuration import settings
from custom_components.ha_energy_price_engine.const import DOMAIN

from .test_integration import price_service, setup  # noqa: F401
from .wizard_helpers import options_advanced


@pytest.mark.usefixtures("price_service")
async def test_direct_supplier_contract_approval_and_compact_review(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(domain="nordpool", entry_id="np", state=ConfigEntryState.LOADED)
    source.add_to_hass(hass)
    entry = await setup(hass)
    original = settings(entry)
    r = await options_advanced(hass, entry.entry_id)
    fid = r["flow_id"]
    r = await hass.config_entries.options.async_configure(fid, {"next_step_id": "wizard_supplier"})
    fields = {str(k): k for k in r["data_schema"].schema}
    assert fields["unit"].default() == "ore/kWh"
    assert "add_contract" not in fields and "verified_on" not in fields
    data = {
        "supplier": "ewii",
        "contract_mode": "verified",
        "amount": 3,
        "unit": "ore/kWh",
        "vat_included": False,
        "rate_vat_percent": 25,
        "valid_from": "2026-10-23",
        "valid_to": "2027-01-01",
        "replace_periods": True,
        "navigation": "review",
    }
    r = await hass.config_entries.options.async_configure(fid, data)
    assert r["errors"]["confirm_verified"] == "verification_required"
    assert settings(entry) == original
    r = await hass.config_entries.options.async_configure(fid, {**data, "confirm_verified": True})
    assert r["step_id"] == "wizard_review"
    assert len(r["menu_options"]) == 3  # Save, Back, Advanced when complete.
    table = r["description_placeholders"]["table"]
    assert table.count("2026-10-23") == 1 and table.count("2026-10-24") == 1
    assert "Verified" in table
    result = await hass.config_entries.options.async_configure(fid, {"next_step_id": "wizard_save"})
    assert result["type"] == "create_entry"
    assert entry.runtime_data.data["status"] == "READY"
    supplier = [r for r in settings(entry)["dated_components"] if r["id"] == "supplier"]
    assert len(supplier) == 2
    assert supplier[0]["valid_to"] == "2026-10-23" and supplier[1]["amount"] == 3
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_permanent_delete_native_confirmation_is_required(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    r = await options_advanced(hass, entry.entry_id)
    fid = r["flow_id"]
    r = await hass.config_entries.options.async_configure(fid, {"next_step_id": "site_management"})
    ledger = entry.runtime_data.price_engine.database.path
    assert ledger.name in r["description_placeholders"]["files"]
    for data in (
        {"operation": "permanent", "site_id": "wrong", "confirm": True},
        {"operation": "permanent", "site_id": "home", "confirm": False},
    ):
        r = await hass.config_entries.options.async_configure(fid, data)
        assert r["errors"]["base"] == "deletion_confirmation"
        defaults = {str(k): k.default() for k in r["data_schema"].schema}
        assert defaults["operation"] == "permanent" and defaults["site_id"] == data["site_id"]
        assert ledger.exists() and entry.entry_id in hass.data[DOMAIN]
    r = await hass.config_entries.options.async_configure(
        fid, {"operation": "permanent", "site_id": "home", "confirm": True}
    )
    assert r["type"] == "abort" and r["reason"] == "site_deleted"
    assert not ledger.exists() and hass.config_entries.async_get_entry(entry.entry_id) is None


@pytest.mark.usefixtures("price_service")
async def test_failed_save_cannot_certify_previous_ready_runtime(hass, freezer):
    from unittest.mock import AsyncMock, patch

    from .wizard_helpers import options_review

    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(domain="nordpool", entry_id="np", state=ConfigEntryState.LOADED)
    source.add_to_hass(hass)
    entry = await setup(hass)
    r = await options_review(hass, entry.entry_id)
    with patch(
        "custom_components.ha_energy_price_engine.apply_settings", AsyncMock(return_value=False)
    ):
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"next_step_id": "wizard_save"}
        )
    assert r["step_id"] == "wizard_saved"
    assert "failed" in r["description_placeholders"]["save_problem"]
    assert "Verified" not in r["description_placeholders"]["table"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)
