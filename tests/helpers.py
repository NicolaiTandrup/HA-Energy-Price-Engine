"""Explicit synthetic marginal contracts and official quarter source fixtures."""

from datetime import UTC, date, datetime, timedelta

from custom_components.ha_energy_price_engine.configuration import tariff_for
from custom_components.ha_energy_price_engine.models import PriceSlot
from custom_components.ha_energy_price_engine.price_engine import day_bounds

NOW = datetime(2026, 10, 23, tzinfo=UTC)


def rule(name, amount, **changes):
    return {
        "id": name,
        "amount": amount,
        "unit": "ore/kWh",
        "vat_included": False,
        "vat_rate": 0.25,
        "valid_from": "2020-01-01",
        "valid_to": "2030-01-01",
        "source": "Synthetic test-only contract",
        "verified_on": "2026-10-23",
        **changes,
    }


def model(**changes):
    return {
        "id": "home",
        "name": "Test home",
        "nordpool_entry": "np",
        "area": "DK2",
        "timezone": "Europe/Copenhagen",
        "vat": 0.25,
        "dso_mode": "manual",
        "dated_components": [rule("supplier", 3), rule("dso", 20)],
        "setup_step": "review",
        **changes,
    }


def tariff(**changes):
    # Long-range rates here are test fixtures, never production defaults.
    value = tariff_for(model())
    value["components"] = [
        rule("supplier", 3),
        rule("dso", 20),
        rule("energinet_net", 4.3),
        rule("energinet_system", 7.2),
        rule("electricity_tax", 0.8),
    ]
    return {**value, **changes}


def rows(day=date(2026, 10, 24), price=-0.1):
    first, last = day_bounds(day)
    return [
        PriceSlot(first + timedelta(minutes=15 * i), first + timedelta(minutes=15 * (i + 1)), price)
        for i in range(int((last - first).total_seconds() / 900))
    ]


def response(day, price=-100):
    return {
        "DK2": [
            {"start": s.start.isoformat(), "end": s.end.isoformat(), "price": price}
            for s in rows(day)
        ]
    }
