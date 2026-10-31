"""Actual native lifecycle, precise API v2 contract, readiness, snapshots and reset."""

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.api import EngineNotReady, Status, get_api
from custom_components.ha_energy_price_engine.const import DOMAIN, PRICE_REVISION_EVENT
from custom_components.ha_energy_price_engine.diagnostics import async_get_config_entry_diagnostics
from custom_components.ha_energy_price_engine.price_engine import day_bounds
from custom_components.ha_energy_price_engine.site_lifecycle import permanently_remove
from custom_components.ha_energy_price_engine.status import statistics

from .helpers import model


async def setup(hass, data=None, **kwargs):
    data = data or model()
    entry = MockConfigEntry(domain=DOMAIN, data=data, unique_id=data["id"], version=4, **kwargs)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_native_multisite_nine_entities_device_version_and_read_only_api(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    home = await setup(hass)
    away = await setup(hass, model(id="away", name="Other site"))
    api = get_api(hass, 2)
    assert {s.site_id for s in api.sites()} == {"home", "away"}
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, home.entry_id)
    assert len(entities) == 9 and all(e.domain == "sensor" for e in entities)
    assert not any(e.disabled for e in entities)
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), home.entry_id)
    assert (
        devices[0].sw_version
        == json.loads(Path("custom_components/ha_energy_price_engine/manifest.json").read_text())[
            "version"
        ]
    )
    first, last = day_bounds(date(2026, 10, 24))
    before = len(price_service["calls"])
    with (
        patch(
            "custom_components.ha_energy_price_engine.price_engine.calculate",
            side_effect=AssertionError("read calculation"),
        ),
        patch.object(
            home.runtime_data.price_engine.database,
            "async_commit",
            side_effect=AssertionError("read write"),
        ),
        patch.object(
            home.runtime_data.price_updater.official,
            "get",
            side_effect=AssertionError("read provider"),
        ),
    ):
        result = api.lookup("home", first, last)
        assert result.status == Status.READY and len(result.slots) == 96
        assert result.currency == "DKK" and result.unit == "DKK/kWh" and result.vat_included
        assert result.slots[0].price == pytest.approx(0.31625)
        assert result.slots[0].verified_at <= datetime.now(UTC)
        with pytest.raises(FrozenInstanceError):
            result.slots[0].price = 100
        assert statistics(home.runtime_data)["used_slots"] == 96
    assert len(price_service["calls"]) == before
    assert await hass.config_entries.async_unload(home.entry_id)
    with pytest.raises(EngineNotReady):
        api.lookup("home", first, last)
    assert api.lookup("away", first, last).status == Status.READY
    assert await hass.config_entries.async_unload(away.entry_id)
    with pytest.raises(EngineNotReady):
        get_api(hass)
    with pytest.raises(ValueError, match="v2"):
        get_api(hass, 1)


async def test_future_correction_exact_revision_and_incomplete_no_quotes(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    api = get_api(hass)
    first, last = day_bounds(date(2026, 10, 25))
    old = api.lookup("home", first, last).slots[0]
    events = []
    hass.bus.async_listen(PRICE_REVISION_EVENT, lambda event: events.append(event.data))
    price_service["amount"] = 200
    await c.schedule.refresh_day(c.site, date(2026, 10, 25), datetime.now(UTC))
    await hass.async_block_till_done()
    new = api.lookup("home", first, last).slots[0]
    assert new.price > old.price and new.revision > old.revision
    assert api.revision("home", first, old.revision) == old
    assert events[-1]["api_version"] == 2 and len(events[-1]["affected_slots"]) == 100
    price_service["partial"] = True
    await c.schedule.refresh_day(c.site, date(2026, 10, 25), datetime.now(UTC))
    result = api.lookup("home", first, last)
    assert result.status == Status.INCOMPLETE and result.slots == () and result.available_slots == 1
    assert len(c.price_engine.lookup("home", first, last)) == 100
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_source_failure_stale_settings_and_historical_cost_ranges(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    api = get_api(hass)
    first, last = day_bounds(date(2026, 10, 24))
    price_service["failure"] = True
    await c.schedule.refresh_day(c.site, date(2026, 10, 24), datetime.now(UTC))
    assert api.lookup("home", first, last).status == Status.ERROR
    assert not api.lookup("home", first, last).slots
    assert api.lookup("home", first, first + timedelta(hours=1)).status == Status.READY
    c.settings_current = False
    assert api.lookup("home", first, last).status in {Status.ERROR, Status.STALE}
    c.schedule.days["home"][str(date(2026, 10, 24))]["status"] = "READY"
    c.schedule.days["home"][str(date(2026, 10, 24))]["last_success"] = "2026-10-25T12:00:00+00:00"
    assert not api.lookup("home", first, last).slots
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_restart_sqlite_and_redacted_diagnostics(hass, freezer, price_service):
    freezer.move_to("2026-10-24T12:07:00Z")
    data = model(name="PRIVATE ADDRESS")
    data["dated_components"][0]["source"] = "PRIVATE ACCOUNT"
    entry = await setup(hass, data)
    before = entry.runtime_data.price_engine.records["home"]
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert "PRIVATE" not in str(diag) and diag["api_version"] == 2 and diag["ledger_records"] == 196
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.price_engine.records["home"] == before
    assert len(er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)) == 9
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_explicit_reset_deletes_only_selected_site_and_history(hass, freezer, price_service):
    freezer.move_to("2026-10-24T12:07:00Z")
    home = await setup(hass)
    other = await setup(hass, model(id="away", name="Away"))
    history = home.runtime_data.price_engine.database.path
    otherpath = other.runtime_data.price_engine.database.path
    otherbytes = otherpath.read_bytes()
    unrelated = history.parent / "home-assistant_v2.db"
    unrelated.write_bytes(b"recorder")
    await permanently_remove(hass, home)
    assert not history.exists() and hass.config_entries.async_get_entry(home.entry_id) is None
    assert otherpath.read_bytes() == otherbytes and unrelated.read_bytes() == b"recorder"
    assert get_api(hass).sites()[0].site_id == "away"
    assert await hass.config_entries.async_unload(other.entry_id)


async def test_old_beta_fails_without_deleting_any_data(hass, price_service, tmp_path):
    entry = MockConfigEntry(
        domain=DOMAIN, data={"id": "old", "name": "Old", "source_type": "entity"}, version=3
    )
    entry.add_to_hass(hass)
    path = tmp_path / "unrelated"
    path.write_bytes(b"keep")
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert path.read_bytes() == b"keep" and entry.data["id"] == "old"
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert flow["step_id"] == "reset"
    hass.config_entries.options.async_abort(flow["flow_id"])
