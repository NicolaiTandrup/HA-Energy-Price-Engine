"""Selected-site removal. Default removal archives; permanent cleanup is explicit."""

import re
from pathlib import Path

from homeassistant.helpers.storage import Store

from .configuration import settings
from .const import DOMAIN


def _safe(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Unsafe site storage identifier")
    return value


def owned_files(hass, entry):
    """Exact prefix boundary and known suffixes only; never follow symlinks."""
    prefix = f"{DOMAIN}.{_safe(entry.entry_id)}."
    legacy = f"{prefix}{_safe(settings(entry)['id'])}.prices"
    root = Path(hass.config.path(".storage"))
    if root.is_symlink():
        raise OSError("Refusing symlinked storage root")
    if not root.exists():
        return []
    files = []
    for path in root.iterdir():
        if not path.name.startswith(prefix):
            continue
        suffix = path.name.removeprefix(prefix)
        known = (
            suffix
            in {
                "configuration",
                "price_schedule",
                "tariffs",
                "ledger.sqlite3",
                "ledger.sqlite3-journal",
                "ledger.sqlite3-wal",
                "ledger.sqlite3-shm",
            }
            or re.fullmatch(r"ledger\.sqlite3\.backup-[a-f0-9]{32}", suffix)
            or path.name in {legacy, legacy + ".migrated"}
        )
        if known:
            if path.is_symlink() or not path.is_file():
                raise OSError("Refusing unexpected site storage object")
            files.append(path)
    return files


async def clear_drafts(hass, entry):
    from asyncio import Lock

    lock = hass.data.setdefault(DOMAIN + "_draft_lock", Lock())
    async with lock:
        store = Store(hass, 1, f"{DOMAIN}.wizard.initial")
        drafts = await store.async_load() or {}
        retained = {
            key: value
            for key, value in drafts.items()
            if value.get("draft", {}).get("id") != settings(entry)["id"]
        }
        if retained != drafts:
            await store.async_save(retained)
        await Store(hass, 1, f"{DOMAIN}.wizard.{entry.entry_id}").async_remove()


async def removed(hass, entry):
    """HA's normal Delete action explicitly retains an archive at its current path."""
    await clear_drafts(hass, entry)
    intents = await Store(hass, 1, f"{DOMAIN}.deletions").async_load() or {}
    if entry.entry_id in intents:
        return
    files = await hass.async_add_executor_job(owned_files, hass, entry)
    archives = Store(hass, 1, f"{DOMAIN}.archives")
    data = await archives.async_load() or {}
    history = [
        p.name
        for p in files
        if ".ledger.sqlite3" in p.name or p.name.endswith((".prices", ".prices.migrated"))
    ]
    data[entry.entry_id] = {
        "site_id": settings(entry)["id"],
        "name": entry.title,
        "files": history,
        "automatic_restore": False,
    }
    await archives.async_save(data)
    for path in files:
        if path.name not in history:
            await hass.async_add_executor_job(path.unlink, True)


async def permanently_remove(hass, entry):
    """Durable intent prevents interrupted cleanup from resuming pricing on restart."""
    from homeassistant.config_entries import ConfigEntryState

    _safe(entry.entry_id)
    intents = Store(hass, 1, f"{DOMAIN}.deletions")
    data = await intents.async_load() or {}
    data[entry.entry_id] = {"permanent": True}
    await intents.async_save(data)
    if entry.state == ConfigEntryState.LOADED:
        if not await hass.config_entries.async_unload(entry.entry_id):
            raise OSError("Site could not be stopped; no history deleted")
    files = await hass.async_add_executor_job(owned_files, hass, entry)
    await clear_drafts(hass, entry)
    for path in files:
        await hass.async_add_executor_job(path.unlink, True)
    archives = Store(hass, 1, f"{DOMAIN}.archives")
    archived = await archives.async_load() or {}
    archived.pop(entry.entry_id, None)
    await archives.async_save(archived)
    await hass.config_entries.async_remove(entry.entry_id)
    # Keep only an entry-ID tombstone. No contract/name/history survives here.
