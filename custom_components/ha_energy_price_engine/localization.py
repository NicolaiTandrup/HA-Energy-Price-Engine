"""Resolve native selector translations for the authenticated frontend user."""

from homeassistant.components.frontend.storage import async_user_store
from homeassistant.helpers.http import current_request
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN


async def user_language(hass):
    language = hass.config.language
    request = current_request.get()
    if request is not None and (user := request.get("hass_user")):
        store = await async_user_store(hass, user.id)
        language = store.data.get("language", {}).get("language", language)
    return language


async def flow_labels(hass):
    """Server-resolved labels prevent empty menu rows with stale client resources."""
    language = await user_language(hass)
    result = {}
    for locale in dict.fromkeys(("en", language.split("-")[0], language)):
        for category in ("config", "options", "selector"):
            result.update(
                {
                    k: v
                    for k, v in (
                        await async_get_translations(hass, locale, category, {DOMAIN})
                    ).items()
                    if v and v.strip()
                }
            )
    return result
