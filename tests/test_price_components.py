"""One marginal formula: bounded public rates, manual overrides and VAT exactly once."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.ha_energy_price_engine.configuration import (
    current_rate,
    tariff_for,
    validate_site,
)
from custom_components.ha_energy_price_engine.models import PriceSlot
from custom_components.ha_energy_price_engine.price_components import (
    compose_dated,
    danish_public_components,
)

from .helpers import model, rule, tariff


def slot(year=2026, price=1):
    first = datetime(year, 10, 24, 12, tzinfo=UTC)
    return PriceSlot(first, first + timedelta(minutes=15), price)


@pytest.mark.parametrize("price", [1, -0.5, -5, 0])
@pytest.mark.parametrize("included", [False, True])
def test_vat_once_and_negative_spot(price, included):
    config = tariff()
    config["components"][0] = rule("supplier", 3.75 if included else 3, vat_included=included)
    total, parts = compose_dated(slot(price=price), config)
    assert total == pytest.approx(price * 1.25 + 0.25 + 0.0375 + 0.05375 + 0.09 + 0.01)
    assert parts["components"]["supplier"]["incl_vat"] == pytest.approx(0.0375)


@pytest.mark.parametrize(
    "year,missing",
    [
        (2026, {"supplier"}),
        (2027, {"supplier", "energinet_net", "energinet_system"}),
        (2028, {"supplier", "energinet_net", "energinet_system", "electricity_tax"}),
    ],
)
def test_public_validity_not_extrapolated(year, missing):
    config = tariff(components=danish_public_components() + [rule("dso", 20)])
    with pytest.raises(ValueError) as err:
        compose_dated(slot(year), config)
    assert set(err.value.components) == missing


def test_locked_override_and_conflicts():
    config = tariff_for(model())
    base, _ = compose_dated(slot(), config)
    config["components"].append(rule("energinet_net", 8, locked=True))
    total, parts = compose_dated(slot(), config)
    assert total == pytest.approx(base - 0.05375 + 0.1)
    assert parts["components"]["energinet_net"]["locked"]
    config["components"].append(deepcopy(config["components"][-1]))
    with pytest.raises(ValueError, match="Overlapping"):
        compose_dated(slot(), config)


@pytest.mark.parametrize(
    "key,value",
    [
        ("supplier_subscription", 4),
        ("source_type", "entity"),
        ("price_basis", "all_in"),
        ("display_unit", "DKK/kWh"),
    ],
)
def test_retired_site_fields_fail_explicitly(key, value):
    with pytest.raises(ValueError, match="Retired"):
        validate_site({**model(), key: value})


@pytest.mark.parametrize(
    "changes",
    [
        {"unit": "DKK/month"},
        {"eligibility": "heating"},
        {"vat_included": "yes"},
        {"amount": True},
        {"hours": [24]},
        {"source": ""},
    ],
)
def test_invalid_rules_fail_closed(changes):
    site = model(dated_components=[{**rule("supplier", 3), **changes}])
    with pytest.raises((ValueError, TypeError)):
        validate_site(site)


def test_from_now_and_explicit_whole_day_are_distinct():
    now = datetime(2026, 10, 24, 12, 7, tzinfo=UTC)
    for whole, expected in [
        (False, "2026-10-24T12:15:00+00:00"),
        (True, "2026-10-23T22:00:00+00:00"),
    ]:
        value = current_rate(
            model(dated_components=[]), "supplier", "3.75", False, now, whole_day=whole
        )
        assert value["dated_components"][0]["effective_after"] == expected
