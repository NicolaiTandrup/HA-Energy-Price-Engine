"""Standalone native Energy Price Engine. No vehicle or charging controls."""

import logging

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .coordinator import PriceCoordinator

PLATFORMS = [Platform.SENSOR]
LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass, config):
    from .dashboard import async_setup_dashboard

    await async_setup_dashboard(hass)
    return True


async def async_migrate_entry(hass, entry):
    """Beta.10 deliberately requires an explicit reset of old beta sites."""
    if entry.version != 4:
        LOGGER.error("Breaking beta.10: back up, remove/re-add this site; no data was deleted")
        return False
    return True


async def async_setup_entry(hass, entry):
    from homeassistant.helpers.storage import Store

    intents = await Store(hass, 1, f"{DOMAIN}.deletions").async_load() or {}
    if entry.entry_id in intents:
        raise ConfigEntryError(
            "Permanent deletion interrupted. Configure this site to retry cleanup."
        )
    try:
        coordinator = PriceCoordinator(hass, entry)
        coordinator.integration_version = str((await async_get_integration(hass, DOMAIN)).version)
    except (ValueError, KeyError, TypeError) as err:
        raise ConfigEntryError("Invalid site configuration; reconfigure this entry") from err
    entry.async_on_unload(coordinator.stop)
    try:
        await coordinator.start()
        entry.runtime_data = coordinator
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as err:
        coordinator.stop()
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if isinstance(err, OSError):
            raise ConfigEntryNotReady("Price storage temporarily unavailable") from err
        raise
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass, entry):
    if runtime := hass.data.get(DOMAIN, {}).get(entry.entry_id):
        runtime.settings_current = False
    waiter = hass.data.get(DOMAIN + "_save_waiters", {}).get(entry.entry_id)
    try:
        loaded = await hass.config_entries.async_reload(entry.entry_id)
    except Exception:
        if waiter and not waiter.done():
            waiter.set_result(False)
        raise
    if waiter and not waiter.done():
        waiter.set_result(loaded)


async def apply_settings(hass, entry, site, *, reuse_sources=False):
    """Await one normal reload, including actual transactional persistence."""
    import asyncio

    waiters = hass.data.setdefault(DOMAIN + "_save_waiters", {})
    if entry.entry_id in waiters:
        return False
    if reuse_sources and (runtime := hass.data.get(DOMAIN, {}).get(entry.entry_id)):
        hass.data.setdefault(DOMAIN + "_reload_sources", {})[entry.entry_id] = (
            runtime.price_updater.official
        )
    waiter = asyncio.get_running_loop().create_future()
    waiters[entry.entry_id] = waiter
    try:
        had_listener = bool(entry.update_listeners)
        changed = hass.config_entries.async_update_entry(entry, title=site["name"], options=site)
        if not changed or not had_listener:
            return await hass.config_entries.async_reload(entry.entry_id)
        async with asyncio.timeout(90):
            return await waiter
    except TimeoutError, OSError:
        return False
    finally:
        waiters.pop(entry.entry_id, None)
        hass.data.get(DOMAIN + "_reload_sources", {}).pop(entry.entry_id, None)


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    entry.runtime_data.stop()
    async with entry.runtime_data.schedule.work_lock:
        pass
    async with entry.runtime_data.price_updater.lock:
        pass
    async with entry.runtime_data.price_engine.lock:
        pass
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    ir.async_delete_issue(hass, DOMAIN, entry.entry_id)
    return True
