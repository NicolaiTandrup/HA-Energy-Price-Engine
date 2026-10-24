"""Standalone native Energy Price Engine. No vehicle or charging controls."""

import logging

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from .configuration import validate_site
from .const import DOMAIN
from .coordinator import PriceCoordinator

PLATFORMS = [Platform.SENSOR]
LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass, entry):
    """Upgrade durable site settings additively, without touching price history."""
    if entry.version > 2:
        LOGGER.error("Cannot load a newer Price Engine entry with this integration version")
        return False
    if entry.version == 1:
        try:
            data = validate_site(dict(entry.data))
            options = validate_site({**data, **entry.options}) if entry.options else {}
        except ValueError, KeyError, TypeError:
            LOGGER.error("Legacy Price Engine entry requires configuration repair")
            return False
        hass.config_entries.async_update_entry(entry, data=data, options=options, version=2)
    return True


async def async_setup_entry(hass, entry):
    try:
        coordinator = PriceCoordinator(hass, entry)
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
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    entry.runtime_data.stop()
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    ir.async_delete_issue(hass, DOMAIN, entry.entry_id)
    return True
