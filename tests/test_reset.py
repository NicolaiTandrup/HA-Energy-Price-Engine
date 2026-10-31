"""Reset isolation, exact path boundaries and interrupted cleanup safety."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.storage import Store

from custom_components.ha_energy_price_engine.api import Status, get_api
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.price_engine import day_bounds
from custom_components.ha_energy_price_engine.site_lifecycle import owned_files, permanently_remove

from .test_integration import setup


async def test_unload_failure_keeps_history_and_fails_closed_with_durable_intent(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    path = entry.runtime_data.price_engine.database.path
    before = path.read_bytes()
    with patch.object(hass.config_entries, "async_unload", AsyncMock(return_value=False)):
        with pytest.raises(OSError, match="no history deleted"):
            await permanently_remove(hass, entry)
    assert path.read_bytes() == before
    assert entry.runtime_data.stopped
    assert get_api(hass).lookup("home", *day_bounds(date(2026, 10, 25))).status == Status.STALE
    assert entry.entry_id in (await Store(hass, 1, f"{DOMAIN}.deletions").async_load())
    await permanently_remove(hass, entry)
    assert not path.exists()


async def test_exact_storage_scope_and_symlink_refusal(hass, freezer, price_service):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    path = entry.runtime_data.price_engine.database.path
    root = path.parent
    near = root / f"{DOMAIN}.{entry.entry_id}other.ledger.sqlite3"
    near.write_bytes(b"other site")
    unknown = root / f"{DOMAIN}.{entry.entry_id}.unrelated"
    unknown.write_bytes(b"not PE owned")
    assert (
        path in owned_files(hass, entry)
        and near not in owned_files(hass, entry)
        and unknown not in owned_files(hass, entry)
    )
    link = root / f"{DOMAIN}.{entry.entry_id}.tariffs"
    link.symlink_to(near)
    with pytest.raises(OSError, match="unexpected"):
        owned_files(hass, entry)
    link.unlink()
    await permanently_remove(hass, entry)
    assert near.read_bytes() == b"other site" and unknown.read_bytes() == b"not PE owned"


async def test_normal_delete_retains_history_and_new_site_cannot_auto_attach(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    path = entry.runtime_data.price_engine.database.path
    before = path.read_bytes()
    await hass.config_entries.async_remove(entry.entry_id)
    assert path.read_bytes() == before
    from .helpers import model

    replacement = await setup(hass, model(id="new_home"))
    assert replacement.runtime_data.price_engine.database.path != path
    assert get_api(hass).sites()[0].site_id == "new_home"
    assert await hass.config_entries.async_unload(replacement.entry_id)
