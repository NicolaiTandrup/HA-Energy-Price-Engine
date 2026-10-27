"""Complete native labels/interpolation and relevant fields in all supported locales."""

import re
from copy import deepcopy

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.const import DOMAIN

from .test_integration import model, price_service, setup  # noqa: F401
from .wizard_helpers import advanced_target, options_review


@pytest.mark.parametrize("language", ["en", "en-GB", "da"])
@pytest.mark.usefixtures("price_service")
async def test_all_advanced_paths_have_labels_and_complete_formatjs_context(
    hass, freezer, language
):
    freezer.move_to("2026-10-27T12:07:00Z")
    hass.config.language = language
    np = MockConfigEntry(
        domain="nordpool", entry_id="np", data={"areas": ["DK2"]}, state=ConfigEntryState.LOADED
    )
    np.add_to_hass(hass)
    data = model()
    data["dated_components"][0].update(amount="0.5", unit="ore/kWh")
    subscription = {
        **data["dated_components"][0],
        "id": "supplier_subscription",
        "amount": 29,
        "unit": "DKK/month",
    }
    data["dated_components"].append(subscription)
    entry = await setup(hass, data)
    accepted = deepcopy(dict(entry.data)), deepcopy(dict(entry.options))
    translations = await async_get_translations(hass, language, "options", {DOMAIN})

    def rendered(result):
        step = result["step_id"]
        prefix = f"component.{DOMAIN}.options.step.{step}."
        context = result.get("description_placeholders", {})
        assert (
            set(re.findall(r"\{([a-z_]+)\}", translations.get(prefix + "description", "")))
            <= context.keys()
        )
        assert "draft_status" in context
        if result["type"] == "menu":
            assert all(
                label.strip() and label != key for key, label in result["menu_options"].items()
            )
        else:
            for key in result["data_schema"].schema:
                label = translations.get(prefix + "data." + str(key))
                assert label and label != str(key), (step, key)

    for target in [
        "rates",
        "source_details",
        "setup_display",
        "setup_offers",
        "setup_estimate",
        "setup_tax_details",
        "storage_tools",
    ]:
        r = await options_review(hass, entry.entry_id)
        rendered(r)
        r = await advanced_target(hass, r["flow_id"], target)
        rendered(r)
        if target == "source_details":
            assert "price_entity" not in {str(k) for k in r["data_schema"].schema}
            r = await hass.config_entries.options.async_configure(
                r["flow_id"], {"timezone": "No/Such_Zone"}
            )
            assert r["errors"] == {"timezone": "invalid_timezone"}
            rendered(r)
            r = await hass.config_entries.options.async_configure(
                r["flow_id"], {"source_type": "entity"}
            )
            assert "price_entity" in {str(k) for k in r["data_schema"].schema}
            rendered(r)
            assert (dict(entry.data), dict(entry.options)) == accepted
        hass.config_entries.options.async_abort(r["flow_id"])
    for target in ("select_quarter", "session_estimate"):
        r = await options_review(hass, entry.entry_id)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"next_step_id": "setup_final"}
        )
        rendered(r)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {"next_step_id": target}
        )
        rendered(r)
        if target == "session_estimate":
            values = {
                "slot": "2026-10-27T12:15:00+00:00",
                "energy": "1,25\n2,0",
                "energy_kind": "measured",
            }
            r = await hass.config_entries.options.async_configure(r["flow_id"], values)
            assert r["errors"] == {"slot": "future_measurement"}
            rendered(r)
            r = await hass.config_entries.options.async_configure(
                r["flow_id"], {**values, "energy_kind": "planned"}
            )
            assert not r["errors"] and "DKK" in r["description_placeholders"]["result"]
            rendered(r)
            assert (dict(entry.data), dict(entry.options)) == accepted
        hass.config_entries.options.async_abort(r["flow_id"])
    r = await options_review(hass, entry.entry_id)
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "setup_supplier"}
    )
    rendered(r)
    default = next(k.default() for k in r["data_schema"].schema if str(k) == "amount")
    assert default == ("0,5" if language == "da" else "0.5")
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"amount": "0,75", "vat_included": True}
    )
    rendered(r)
    assert [x for x in entry.options["dated_components"] if x["id"] == "supplier_subscription"] == [
        subscription
    ]
    assert await hass.config_entries.async_unload(entry.entry_id)
    np.mock_state(hass, ConfigEntryState.NOT_LOADED)
