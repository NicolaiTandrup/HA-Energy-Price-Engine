"""Use real Home Assistant test fixtures with custom integration loading."""

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def hass_config_dir(tmp_path):
    """Real SQLite files must be isolated per test, not in the plugin install tree."""
    return str(tmp_path)


@pytest.fixture
async def price_service(hass):
    from datetime import date

    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.core import SupportsResponse
    from pytest_homeassistant_custom_component.common import (
        MockConfigEntry,
        MockModule,
        mock_integration,
    )

    from .helpers import response

    values = {"amount": -100, "partial": False, "failure": False, "empty": False, "calls": []}

    async def prices(call):
        from homeassistant.exceptions import HomeAssistantError

        values["calls"].append(dict(call.data))
        if values["failure"]:
            raise HomeAssistantError("Synthetic provider outage")
        result = response(date.fromisoformat(call.data["date"]), values["amount"])
        if values["partial"]:
            result["DK2"] = result["DK2"][:1]
        if values["empty"]:
            result["DK2"] = []
        return result

    mock_integration(hass, MockModule("nordpool"))
    provider = MockConfigEntry(
        domain="nordpool",
        entry_id="np",
        data={"areas": ["DK2"], "currency": "DKK"},
        state=ConfigEntryState.LOADED,
    )
    provider.add_to_hass(hass)
    hass.services.async_register(
        "nordpool", "get_prices_for_date", prices, supports_response=SupportsResponse.ONLY
    )
    yield values
    provider.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.fixture
async def radius_source():
    import json
    from pathlib import Path
    from unittest.mock import patch

    from custom_components.ha_energy_price_engine.tariff_source import (
        RADIUS_CODE,
        RADIUS_GLN,
        normalize_tariffs,
    )

    records = json.loads((Path(__file__).parent / "fixtures/radius_c_datahub.json").read_text())

    async def get(self, site, start, end, now):
        slots, meta = normalize_tariffs(records, RADIUS_GLN, RADIUS_CODE, start, end)
        return slots, {**meta, "fetched_at": now.isoformat()}

    with patch("custom_components.ha_energy_price_engine.tariff_source.TariffSource.get", get):
        yield
