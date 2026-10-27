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
    from .wizard_helpers import options_review

    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(
        domain="nordpool", entry_id="np", data={"areas": ["DK2"]}, state=ConfigEntryState.LOADED
    )
    source.add_to_hass(hass)
    entry = await setup(hass)
    r = await options_review(hass, entry.entry_id)
    fid = r["flow_id"]
    r = await hass.config_entries.options.async_configure(fid, {"next_step_id": "setup_supplier"})
    data = {"amount": "3", "vat_included": False}
    r = await hass.config_entries.options.async_configure(fid, {**data, "amount": "3..0"})
    assert r["errors"]["amount"] == "invalid_decimal"
    r = await hass.config_entries.options.async_configure(fid, data)
    assert r["step_id"] == "setup_review" and len(r["menu_options"]) == 9
    coverage = r["description_placeholders"]["coverage"]
    assert coverage.count("2026-10-23") == 1 and coverage.count("2026-10-24") == 1
    assert "Verified" in r["menu_options"]["setup_supplier"]
    supplier = [v for v in settings(entry)["dated_components"] if v["id"] == "supplier"]
    assert (
        len(supplier) == 2
        and supplier[0]["valid_to"] == "2026-10-23"
        and supplier[1]["amount"] == "3"
    )
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_permanent_delete_native_confirmation_is_required(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    r = await options_advanced(hass, entry.entry_id)
    fid = r["flow_id"]
    r = await hass.config_entries.options.async_configure(fid, {"next_step_id": "storage_tools"})
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
    from datetime import date
    from unittest.mock import AsyncMock, patch

    from custom_components.ha_energy_price_engine import apply_settings
    from custom_components.ha_energy_price_engine.api import Status, get_api
    from custom_components.ha_energy_price_engine.component_status import component_snapshot
    from custom_components.ha_energy_price_engine.price_engine import day_bounds

    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    proposed = {**settings(entry), "name": "Accepted new name"}
    with patch.object(hass.config_entries, "async_reload", AsyncMock(return_value=False)):
        assert not await apply_settings(hass, entry, proposed)
    assert get_api(hass).lookup("home", *day_bounds(date(2026, 10, 24))).status == Status.STALE
    assert component_snapshot(hass, entry)["components"]["final"]["status"] != "verified"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "admin,address",
    [
        (False, ("127.0.0.1", 8123)),
        (True, ("8.8.8.8", 8123)),
        (True, ("0.0.0.0", 8123)),
        (True, ("224.0.0.1", 8123)),
    ],
)
async def test_hacs_channel_never_forwards_credentials_to_nonlocal_socket(hass, admin, address):
    from types import SimpleNamespace
    from unittest.mock import Mock, patch

    from homeassistant.helpers.http import current_request

    from custom_components.ha_energy_price_engine.hacs_channel import enable_beta_channel

    class Request(dict):
        headers = {"Authorization": "Bearer synthetic-test-token", "Host": "attacker.invalid"}
        transport = Mock()

    request = Request(hass_user=SimpleNamespace(is_admin=admin))
    request.transport.get_extra_info.return_value = address
    token = current_request.set(request)
    try:
        with patch(
            "custom_components.ha_energy_price_engine.hacs_channel.async_get_clientsession",
            side_effect=AssertionError("No network allowed"),
        ):
            with pytest.raises(ValueError):
                await enable_beta_channel(hass)
    finally:
        current_request.reset(token)
