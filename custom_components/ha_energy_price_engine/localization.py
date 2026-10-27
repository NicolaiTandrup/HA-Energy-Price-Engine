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


async def review_labels(hass):
    language = await user_language(hass)
    translations = {}
    for locale in dict.fromkeys(("en", language.split("-")[0], language)):
        translations.update(await async_get_translations(hass, locale, "selector", {DOMAIN}))
    prefix = f"component.{DOMAIN}.selector.review.options."
    result = {
        key.removeprefix(prefix): value
        for key, value in translations.items()
        if key.startswith(prefix)
    }

    request = current_request.get()
    if request is not None and (user := request.get("hass_user")):
        store = await async_user_store(hass, user.id)
        mode = store.data.get("language", {}).get("number_format", "language")
        if mode in {"decimal_comma", "space_comma"}:
            result["decimal_separator"] = ","
        elif mode in {"comma_decimal", "quote_decimal", "none"}:
            result["decimal_separator"] = "."
        elif mode == "system":
            from babel.core import UnknownLocaleError
            from babel.numbers import get_decimal_symbol

            locale = request.headers.get("Accept-Language", language).split(",")[0].split(";")[0]
            try:
                result["decimal_separator"] = get_decimal_symbol(locale.replace("-", "_"))
            except UnknownLocaleError, ValueError:
                pass
    return result
