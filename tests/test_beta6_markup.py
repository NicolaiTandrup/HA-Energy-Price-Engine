"""Real native three-decision flow, fractional money and preserved charging API."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.money import decimal_amount

from .test_integration import price_service  # noqa: F401


@pytest.mark.parametrize(
    "value,expected",
    [("0.25", "0.25"), ("0,50", "0.5"), ("0.75", "0.75"), ("3.125", "3.125"), ("0", "0")],
)
def test_fractional_money_is_not_rounded(value, expected):
    assert decimal_amount(value) == expected


@pytest.mark.parametrize("value", ["-0.1", "NaN", "Infinity", "1,234.56", "0..25", "", True])
def test_ambiguous_or_nonfinite_money_is_rejected(value):
    with pytest.raises(ValueError):
        decimal_amount(value)


@pytest.mark.parametrize("amount", ["0.25", "0,50", "0.75", "3.125"])
@pytest.mark.parametrize("included", [True, False])
@pytest.mark.usefixtures("price_service")
async def test_three_decisions_fractional_markup_persists_and_api_is_ready(
    hass, freezer, amount, included
):
    freezer.move_to("2026-10-27T16:07:00Z")
    np = MockConfigEntry(
        domain="nordpool", entry_id="np", data={"areas": ["DK2"]}, state=ConfigEntryState.LOADED
    )
    np.add_to_hass(hass)
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    fid = r["flow_id"]
    r = await hass.config_entries.flow.async_configure(
        fid, {"name": "Fractional charging", "nordpool_entry": "np"}
    )
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert r["step_id"] == "setup_grid"
    await hass.config_entries.flow.async_configure(fid, {"grid": "manual"})
    r = await hass.config_entries.flow.async_configure(
        fid, {"amount": 20, "vat_included": False, "confirm": True}
    )
    assert r["step_id"] == "setup_supplier"
    assert {str(k) for k in r["data_schema"].schema} == {"amount", "vat_included"}
    r = await hass.config_entries.flow.async_configure(
        fid, {"amount": amount, "vat_included": included}
    )
    assert r["step_id"] == "setup_review" and all(r["menu_options"].values())
    rule = next(x for x in entry.options["dated_components"] if x["id"] == "supplier")
    assert Decimal(rule["amount"]) == Decimal(amount.replace(",", "."))
    assert rule["vat_included"] is included
    start = datetime(2026, 10, 27, 16, 15, tzinfo=UTC)
    result = get_api(hass).lookup(entry.data["id"], start, start + timedelta(minutes=15))
    assert str(result.status) == "READY"
    expected = float(
        (Decimal("-.1") + Decimal(".2") + Decimal(".123")) * Decimal("1.25")
        + Decimal(amount.replace(",", ".")) / 100 * (1 if included else Decimal("1.25"))
    )
    assert result.records[0].final_price_incl_vat == pytest.approx(expected, abs=1e-12)
    hass.config_entries.flow.async_abort(fid)
    r = await hass.config_entries.options.async_init(entry.entry_id)
    assert r["step_id"] == "setup_review"
    assert await hass.config_entries.async_unload(entry.entry_id)
    np.mock_state(hass, ConfigEntryState.NOT_LOADED)
