"""Standalone native Energy Price Engine. No vehicle or charging controls."""

from homeassistant.const import Platform
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .coordinator import PriceCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass, entry):
    coordinator = PriceCoordinator(hass, entry)
    await coordinator.start()
    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    entry.runtime_data.stop()
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    ir.async_delete_issue(hass, DOMAIN, entry.entry_id)
    return True
