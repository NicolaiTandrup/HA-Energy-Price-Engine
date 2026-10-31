"""MVP domain and deliberately breaking consumer contract identifiers."""

DOMAIN = "ha_energy_price_engine"
API_VERSION = 2
PRICE_REVISION_EVENT = f"{DOMAIN}_price_revision_v2"
COMPONENTS = ("supplier", "dso", "energinet_net", "energinet_system", "electricity_tax")
