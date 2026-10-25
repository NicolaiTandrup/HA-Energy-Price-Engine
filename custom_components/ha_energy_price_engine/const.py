"""Public domain and contract identifiers."""

DOMAIN = "ha_energy_price_engine"
API_VERSION = 1
PRICE_REVISION_EVENT = f"{DOMAIN}_price_revision_v1"
COMPONENTS = (
    "supplier",
    "dso",
    "energinet_net",
    "energinet_system",
    "electricity_tax",
    "subscription",
    "supplier_subscription",
    "grid_subscription",
)
