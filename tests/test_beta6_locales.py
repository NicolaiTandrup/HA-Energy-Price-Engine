"""Resolve real HA translations, including the owner's British English locale."""

import pytest
from homeassistant.helpers.translation import async_get_translations

from custom_components.ha_energy_price_engine.const import DOMAIN


@pytest.mark.parametrize("language", ["en", "en-GB", "da"])
@pytest.mark.parametrize("category", ["config", "options"])
async def test_native_flow_resources_resolve_fields_and_navigation(hass, language, category):
    resources = await async_get_translations(hass, language, category, {DOMAIN}, config_flow=True)
    prefix = f"component.{DOMAIN}.{category}.step."
    for field in ("amount", "vat_included", "monthly", "estimate", "confirm"):
        label = resources.get(prefix + "setup_contract.data." + field)
        assert label and label != field
    for target in ("setup_tax", "rates", "setup_review"):
        label = resources.get(prefix + "setup_tax_details.menu_options." + target)
        assert label and label != target
    assert "{draft_status}" not in resources[prefix + "advanced.description"]
