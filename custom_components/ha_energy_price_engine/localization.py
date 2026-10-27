"""Resolve native selector translations for the authenticated frontend user."""

from homeassistant.components.frontend.storage import async_user_store
from homeassistant.helpers.http import current_request
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN


async def review_labels(hass):
    language = hass.config.language
    request = current_request.get()
    if request is not None and (user := request.get("hass_user")):
        store = await async_user_store(hass, user.id)
        language = store.data.get("language", {}).get("language", language)
    translations = await async_get_translations(hass, language, "selector", {DOMAIN})
    prefix = f"component.{DOMAIN}.selector.review.options."
    return {
        key.removeprefix(prefix): value
        for key, value in translations.items()
        if key.startswith(prefix)
    }
