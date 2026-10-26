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
