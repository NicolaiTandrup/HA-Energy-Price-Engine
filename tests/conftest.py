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


@pytest.fixture(autouse=True)
def published_release_feed():
    from unittest.mock import AsyncMock, patch

    with (
        patch(
            "custom_components.ha_energy_price_engine.supplier_offers._fetch",
            AsyncMock(side_effect=OSError("Offline source fixture")),
        ),
        patch(
            "custom_components.ha_energy_price_engine.update.fetch_releases",
            AsyncMock(return_value=[]),
        ),
    ):
        yield
