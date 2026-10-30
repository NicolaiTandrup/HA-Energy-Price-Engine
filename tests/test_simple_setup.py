"""Native flow manager acceptance: saved pages, reopen, current prices and corrections."""

from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.api import Status, get_api
from custom_components.ha_energy_price_engine.component_status import component_snapshot
from custom_components.ha_energy_price_engine.const import DOMAIN

from .test_integration import price_service  # noqa: F401


@pytest.fixture
async def official(hass):
    entry = MockConfigEntry(
        domain="nordpool", entry_id="np", data={"areas": ["DK2"]}, state=ConfigEntryState.LOADED
    )
    entry.add_to_hass(hass)
    yield entry
    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service", "official")
async def test_new_site_saves_every_step_and_reopens_without_final_commit(hass, freezer):
    freezer.move_to("2026-10-27T16:07:00Z")
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert r["step_id"] == "setup_site"
    assert {str(k) for k in r["data_schema"].schema} == {"name", "nordpool_entry"}
    fid = r["flow_id"]
    r = await hass.config_entries.flow.async_configure(
        fid, {"name": "Current site", "nordpool_entry": "np"}
    )
    assert r["step_id"] == "setup_grid"
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    site = entries[0]
    assert site.unique_id == "current_site" and site.data["timezone"] == "Europe/Copenhagen"
    assert site.data["danish_public_rates"] is True
    hass.config_entries.flow.async_abort(fid)
    r = await hass.config_entries.options.async_init(site.entry_id)
    assert r["step_id"] == "setup_grid"  # Actual entry exists; no draft selection.
    fid = r["flow_id"]
    r = await hass.config_entries.options.async_configure(fid, {"grid": "manual"})
    assert r["step_id"] == "setup_grid_rate"
    r = await hass.config_entries.options.async_configure(
        fid, {"amount": 20, "vat_included": False, "confirm": True}
    )
    assert r["step_id"] == "setup_supplier"
    from custom_components.ha_energy_price_engine.sensor import PricingProblemSensor

    assert PricingProblemSensor(site.runtime_data).native_value == "supplier"
    assert site.options["dated_components"][0]["id"] == "dso"
    assert not {"valid_from", "valid_to", "verified_on", "monthly", "product"} & {
        str(k) for k in r["data_schema"].schema
    }
    r = await hass.config_entries.options.async_configure(
        fid, {"amount": "11..1", "vat_included": False}
    )
    assert r["errors"]["amount"] == "invalid_decimal"
    r = await hass.config_entries.options.async_configure(
        fid, {"amount": "11.1", "vat_included": False}
    )
    assert r["step_id"] == "setup_review"
    assert any(x["id"] == "supplier" for x in site.options["dated_components"])
    hass.config_entries.options.async_abort(fid)
    r = await hass.config_entries.options.async_init(site.entry_id)
    assert r["step_id"] == "setup_review" and "horizon" in r["menu_options"]
    assert "wizard_save" not in r["menu_options"] and "setup_done" in r["menu_options"]
    options = dict(site.options)
    done = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "setup_done"}
    )
    assert done["type"] == "create_entry"
    assert dict(site.options) == options
    start = datetime(2026, 10, 27, 16, 15, tzinfo=UTC)
    result = get_api(hass).lookup("current_site", start, start + timedelta(minutes=15))
    assert result.status == Status.READY
    assert result.records[0].final_price_incl_vat == pytest.approx(
        (-0.1 + 0.2 + 0.111 + 0.043 + 0.072 + 0.008) * 1.25
    )
    snapshot = component_snapshot(hass, site)
    assert snapshot["components"]["supplier"]["value"] == pytest.approx(11.1)
    assert snapshot["components"]["final"]["status"] == "verified"
    assert all(row.start >= start for row in site.runtime_data.price_engine.records["current_site"])
    assert await hass.config_entries.async_unload(site.entry_id)


@pytest.mark.usefixtures("price_service", "official")
async def test_provisional_and_missing_are_actionable_and_never_ready(hass, freezer):
    freezer.move_to("2026-10-27T16:07:00Z")
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    fid = r["flow_id"]
    r = await hass.config_entries.flow.async_configure(
        fid, {"name": "Estimate", "nordpool_entry": "np"}
    )
    r = await hass.config_entries.flow.async_configure(fid, {"grid": "manual"})
    r = await hass.config_entries.flow.async_configure(
        fid, {"amount": 20, "vat_included": False, "confirm": True}
    )
    await hass.config_entries.flow.async_configure(fid, {"vat_included": True})
    from .wizard_helpers import advanced_target

    await advanced_target(hass, fid, "setup_estimate", options=False)
    r = await hass.config_entries.flow.async_configure(
        fid, {"amount": "11.1", "vat_included": False, "confirm": True}
    )
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    snapshot = component_snapshot(hass, entry)
    assert snapshot["components"]["supplier"]["status"] == "provisional"
    assert snapshot["components"]["final"]["status"] == "provisional"
    assert snapshot[
        "api_status"
    ] == "INCOMPLETE" and not entry.runtime_data.price_engine.records.get("estimate")
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service", "official")
async def test_confirmed_ewii_offer_requires_explicit_vat_without_dates(hass, freezer):
    from unittest.mock import AsyncMock, patch

    from custom_components.ha_energy_price_engine.supplier_offers import parse_offer

    from .test_supplier_offers import page

    freezer.move_to("2026-10-27T18:07:00Z")
    offer = parse_offer("ewii_basis", page(), "", datetime(2026, 10, 27, 18, 7, tzinfo=UTC))
    with patch(
        "custom_components.ha_energy_price_engine.supplier_offers.get_offers",
        AsyncMock(return_value={"ewii_basis": offer}),
    ):
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        fid = r["flow_id"]
        await hass.config_entries.flow.async_configure(
            fid, {"name": "EWII confirmed", "nordpool_entry": "np"}
        )
        await hass.config_entries.flow.async_configure(fid, {"grid": "manual"})
        await hass.config_entries.flow.async_configure(
            fid, {"amount": 20, "vat_included": False, "confirm": True}
        )
        await hass.config_entries.flow.async_configure(fid, {"vat_included": True})
        from .wizard_helpers import advanced_target

        await advanced_target(hass, fid, "setup_offers", options=False)
        r = await hass.config_entries.flow.async_configure(fid, {"product": "ewii_basis"})
        fields = {str(k) for k in r["data_schema"].schema}
        assert fields == {"vat_basis", "estimate", "confirm"}
        assert "16.5" in r["description_placeholders"]["quote"]
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        assert not any(x["id"] == "supplier" for x in entry.options["dated_components"])
        r = await hass.config_entries.flow.async_configure(
            fid, {"vat_basis": "included", "estimate": False, "confirm": True}
        )
        assert r["step_id"] == "setup_review"
        snapshot = component_snapshot(hass, entry)
        assert snapshot["components"]["supplier"]["value"] == pytest.approx(13.2)
        assert snapshot["api_status"] == "READY"
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_ambiguous_area_is_confirmed_in_same_saved_first_step(hass, freezer):
    freezer.move_to("2026-10-27T18:07:00Z")
    source = MockConfigEntry(
        domain="nordpool",
        entry_id="both",
        data={"areas": ["DK1", "DK2"]},
        state=ConfigEntryState.LOADED,
    )
    source.add_to_hass(hass)
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert {str(k) for k in r["data_schema"].schema} == {"name", "nordpool_entry", "area"}
    r = await hass.config_entries.flow.async_configure(
        r["flow_id"], {"name": "Chosen area", "nordpool_entry": "both", "area": "DK2"}
    )
    assert r["step_id"] == "setup_grid"
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.data["area"] == "DK2"
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)
