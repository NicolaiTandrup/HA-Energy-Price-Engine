"""Provisional contract visualization cannot certify prices or reach consumers."""

from datetime import date

import pytest

from custom_components.ha_energy_price_engine.api import Status, get_api
from custom_components.ha_energy_price_engine.configuration import validate_site
from custom_components.ha_energy_price_engine.price_engine import day_bounds
from custom_components.ha_energy_price_engine.sensor import EstimatedPriceSensor
from custom_components.ha_energy_price_engine.verification import verify_site

from .test_integration import model, price_service, setup  # noqa: F401


def provisional():
    return {
        "amount": 11,
        "unit": "ore/kWh",
        "vat_included": False,
        "vat_rate": 0.25,
        "valid_from": "2026-01-01",
        "valid_to": "2027-01-01",
        "approved": True,
        "approved_on": "2026-10-23",
    }


@pytest.mark.parametrize("day,count", [("2026-10-23", 96), ("2026-03-29", 92), ("2026-10-25", 100)])
@pytest.mark.usefixtures("price_service")
async def test_provisional_is_not_verified_or_durable(hass, freezer, day, count):
    freezer.move_to(day + "T12:00:00Z")
    data = model()
    data["dated_components"] = [r for r in data["dated_components"] if r["id"] != "supplier"]
    data["provisional_supplier"] = provisional()
    preview = await verify_site(hass, validate_site(data))
    assert preview[day]["status"] == "INCOMPLETE"
    assert preview[day]["estimated_slots"] == count
    entry = await setup(hass, data)
    c = entry.runtime_data
    rows = c.price_updater.estimated_slots[day]
    assert len(rows) == count
    assert rows[0].price == pytest.approx((-0.1 + 0.2 + 0.11 + 0.043 + 0.072 + 0.008) * 1.25)
    result = get_api(hass).lookup("home", *day_bounds(date.fromisoformat(day)))
    assert result.status == Status.INCOMPLETE and not result.records
    assert not c.price_engine.records.get("home")
    assert c.schedule.days["home"][day]["grid_status"] == "READY"
    sensor = EstimatedPriceSensor(c)
    assert sensor.native_value == pytest.approx(rows[0].price)
    assert sensor.extra_state_attributes["eligible_for_control"] is False
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert not entry.runtime_data.price_engine.records.get("home")
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "change",
    [{"approved": False}, {"approved_on": ""}, {"amount": True}, {"valid_to": "2025-01-01"}],
)
def test_estimates_require_explicit_valid_input(change):
    with pytest.raises(ValueError):
        validate_site({**model(), "provisional_supplier": {**provisional(), **change}})


@pytest.mark.usefixtures("price_service")
async def test_no_estimate_from_unapproved_missing_or_stale_components(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    data = model()
    data["dated_components"] = []
    data["provisional_supplier"] = provisional()
    entry = await setup(hass, data)
    assert not any(entry.runtime_data.price_updater.estimated_slots.values())
    assert await hass.config_entries.async_unload(entry.entry_id)
