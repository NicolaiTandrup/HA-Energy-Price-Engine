"""Selected-site cleanup, recovery intent and default archive isolation."""

from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.site_lifecycle import owned_files, permanently_remove

from .test_integration import model, price_service, setup  # noqa: F401


@pytest.mark.usefixtures("price_service")
async def test_archive_and_permanent_delete_isolate_other_site_and_recorder(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    first = await setup(hass)
    second = await setup(hass, model("second"))
    ledger = first.runtime_data.price_engine.database.path
    other_ledger = second.runtime_data.price_engine.database.path
    before = await hass.async_add_executor_job(other_ledger.read_bytes)
    global_db = Path(hass.config.path("home-assistant_v2.db"))
    await hass.async_add_executor_job(global_db.write_bytes, b"global recorder must not be touched")
    await Store(hass, 1, f"{DOMAIN}.wizard.initial").async_save(
        {"old": {"draft": model(), "submitted": True}, "other": {"draft": model("second")}}
    )
    await Store(hass, 1, f"{DOMAIN}.wizard.{first.entry_id}").async_save({"draft": model()})
    await permanently_remove(hass, first)
    await hass.async_block_till_done()
    assert not ledger.exists() and hass.config_entries.async_get_entry(first.entry_id) is None
    assert not er.async_entries_for_config_entry(er.async_get(hass), first.entry_id)
    assert not dr.async_entries_for_config_entry(dr.async_get(hass), first.entry_id)
    assert not await Store(hass, 1, f"{DOMAIN}.wizard.{first.entry_id}").async_load()
    drafts = await Store(hass, 1, f"{DOMAIN}.wizard.initial").async_load()
    assert set(drafts) == {"other"}
    assert await hass.async_add_executor_job(other_ledger.read_bytes) == before
    assert (
        await hass.async_add_executor_job(global_db.read_bytes)
        == b"global recorder must not be touched"
    )
    # A fresh same-name site has a new entry identity and a clean empty database.
    fresh = await setup(hass, {**model(), "dated_components": []})
    assert fresh.entry_id != first.entry_id and not fresh.runtime_data.price_engine.records.get(
        "home"
    )
    assert await hass.config_entries.async_unload(fresh.entry_id)
    await hass.config_entries.async_remove(second.entry_id)
    assert other_ledger.exists()
    archive = await Store(hass, 1, f"{DOMAIN}.archives").async_load()
    assert archive[second.entry_id]["files"] == [other_ledger.name]
    assert archive[second.entry_id]["automatic_restore"] is False


@pytest.mark.usefixtures("price_service")
async def test_interrupted_cleanup_stays_stopped_until_retry(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    with patch(
        "custom_components.ha_energy_price_engine.site_lifecycle.owned_files",
        side_effect=OSError("Disk failure"),
    ):
        with pytest.raises(OSError):
            await permanently_remove(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN]
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.entry_id not in hass.data[DOMAIN]
    await permanently_remove(hass, entry)
    assert hass.config_entries.async_get_entry(entry.entry_id) is None


@pytest.mark.usefixtures("price_service")
async def test_unexpected_symlink_aborts_without_touching_target(hass, freezer, tmp_path):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    target = tmp_path / "keep.sqlite"
    target.write_bytes(b"never follow me")
    link = entry.runtime_data.price_engine.database.path.with_name(
        f"{DOMAIN}.{entry.entry_id}.ledger.sqlite3.backup-" + "a" * 32
    )
    link.symlink_to(target)
    with pytest.raises(OSError):
        await hass.async_add_executor_job(owned_files, hass, entry)
    assert target.read_bytes() == b"never follow me"
    link.unlink()
    await permanently_remove(hass, entry)


@pytest.mark.usefixtures("price_service")
async def test_concurrent_selected_site_deletions_keep_both_recovery_intents(hass, freezer):
    import asyncio

    freezer.move_to("2026-10-23T12:00:00Z")
    a = await setup(hass)
    b = await setup(hass, model("second"))
    await asyncio.gather(permanently_remove(hass, a), permanently_remove(hass, b))
    intents = await Store(hass, 1, f"{DOMAIN}.deletions").async_load()
    assert set(intents) == {a.entry_id, b.entry_id}
    assert not hass.config_entries.async_entries(DOMAIN)
