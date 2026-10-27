"""Published semantic release metadata only. Installation stays in HACS.

HACS owns its separate update entity. Never patch HACS or offer branch commits.
"""

import logging
import re
from asyncio import Lock
from datetime import timedelta
from time import monotonic

from awesomeversion import AwesomeVersion
from homeassistant.components.update import UpdateEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

URL = "https://api.github.com/repos/NicolaiTandrup/HA-Energy-Price-Engine/releases"


def release_for(releases, installed):
    """Installed beta follows published beta/stable; stable never follows beta/SHA."""
    current = AwesomeVersion(installed.removeprefix("v"))
    eligible = []
    for release in releases:
        tag = release.get("tag_name", "")
        if release.get("draft") or not re.fullmatch(r"v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", tag):
            continue
        version = AwesomeVersion(tag.removeprefix("v"))
        if (
            release.get("prerelease")
            or version.beta
            or version.alpha
            or version.dev
            or version.release_candidate
        ) and not (current.beta or current.alpha or current.dev or current.release_candidate):
            continue
        if version >= current:
            eligible.append((version, release))
    return max(eligible, key=lambda pair: pair[0])[1] if eligible else None


async def fetch_releases(hass):
    async with async_get_clientsession(hass).get(URL, timeout=10) as response:
        response.raise_for_status()
        return await response.json()


async def async_setup_entry(hass, entry, async_add_entities):
    version = entry.runtime_data.integration_version
    cache = hass.data.setdefault(
        DOMAIN + "_release_metadata", {"lock": Lock(), "fetched": -999999, "data": []}
    )

    async def fetch():
        async with cache["lock"]:
            if monotonic() - cache["fetched"] < 21600:
                return cache["data"]
            try:
                data = await fetch_releases(hass)
                if not isinstance(data, list):
                    raise ValueError("Invalid releases response")
                cache.update(data=data, fetched=monotonic())
                return data
            except Exception as err:
                raise UpdateFailed("Published release metadata unavailable") from err

    coordinator = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name="PE published releases",
        update_method=fetch,
        update_interval=timedelta(hours=6),
        config_entry=entry,
    )
    # Provider price setup is independent; GitHub cannot certify pricing readiness.
    await coordinator.async_refresh()
    async_add_entities([PublishedRelease(coordinator, entry, version)])


class PublishedRelease(CoordinatorEntity, UpdateEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "published_release"

    def __init__(self, coordinator, entry, installed):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['id']}_published_release"
        self._attr_installed_version = installed
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.data["id"])}}

    @property
    def latest_version(self):
        release = release_for(self.coordinator.data or [], self.installed_version)
        return release["tag_name"].removeprefix("v") if release else self.installed_version

    @property
    def release_url(self):
        return f"https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases/tag/v{self.latest_version}"

    @property
    def release_summary(self):
        release = release_for(self.coordinator.data or [], self.installed_version)
        return release.get("body") if release else None
