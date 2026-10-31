"""Explicit entry-scoped development reset, with durable interrupted-delete intent."""

import re
from asyncio import Lock
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
        if not path.name.startswith(prefix) and path.name != f"{DOMAIN}.wizard.{entry.entry_id}":
            continue
        suffix = path.name.removeprefix(prefix)
        known = (
            path.name == f"{DOMAIN}.wizard.{entry.entry_id}"
            or suffix
            in {
                "configuration",
                "setup",
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


async def permanently_remove(hass, entry):
    """Durable intent prevents interrupted cleanup from resuming pricing on restart."""
    from homeassistant.config_entries import ConfigEntryState

    _safe(entry.entry_id)
    async with hass.data.setdefault(DOMAIN + "_catalog_lock", Lock()):
        intents = Store(hass, 1, f"{DOMAIN}.deletions")
        data = await intents.async_load() or {}
        data[entry.entry_id] = {"permanent": True}
        await intents.async_save(data)
    if runtime := hass.data.get(DOMAIN, {}).get(entry.entry_id):
        runtime.settings_current = False
        runtime.stop()
    if entry.state == ConfigEntryState.LOADED:
        if not await hass.config_entries.async_unload(entry.entry_id):
            raise OSError("Site could not be stopped; no history deleted")
    files = await hass.async_add_executor_job(owned_files, hass, entry)
    for path in files:
        await hass.async_add_executor_job(path.unlink, True)
    await hass.config_entries.async_remove(entry.entry_id)
    # Keep only an entry-ID tombstone. No contract/name/history survives here.
