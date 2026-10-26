"""Dated native manual time bands, DST coverage and separate subscriptions."""

from copy import deepcopy
from datetime import date
from zoneinfo import ZoneInfo

import pytest

from custom_components.ha_energy_price_engine.configuration import tariff_for, validate_site
from custom_components.ha_energy_price_engine.price_components import compose_dated

from .test_integration import model
from .test_price_engine import rows


def timeband_site():
    site = model()
    dso = site["dated_components"].pop()
    for hours, amount in [
        (list(range(6)), 4),
        (list(range(6, 17)) + list(range(21, 24)), 8),
        (list(range(17, 21)), 12),
    ]:
        site["dated_components"].append({**dso, "hours": hours, "amount": amount})
    return site


@pytest.mark.parametrize(
    "day,count", [(date(2026, 3, 29), 92), (date(2026, 10, 24), 96), (date(2026, 10, 25), 100)]
)
def test_manual_bands_cover_every_dst_interval_without_utc_hour_guessing(day, count):
    site = validate_site(timeband_site())
    data = rows(day)
    assert len(data) == count
    for slot in data:
        _, parts = compose_dated(slot, tariff_for(site))
        hour = slot.start.astimezone(ZoneInfo(site["timezone"])).hour
        expected = 0.04 if hour < 6 else 0.12 if 17 <= hour < 21 else 0.08
        assert parts["components"]["dso"]["ex_vat"] == expected


def test_overlapping_hours_and_unknown_missing_band_fail_closed():
    site = timeband_site()
    site["dated_components"][-1]["hours"].append(6)
    with pytest.raises(ValueError, match="Overlapping"):
        validate_site(site)
    site = timeband_site()
    site["dated_components"] = [
        r for r in site["dated_components"] if r.get("hours") != list(range(6))
    ]
    with pytest.raises(ValueError, match="Missing verified DSO"):
        compose_dated(rows()[0], tariff_for(validate_site(site)))


def test_supplier_and_grid_fixed_subscriptions_never_enter_slot_ranking():
    site = timeband_site()
    slot = rows()[0]
    original, _ = compose_dated(slot, tariff_for(site))
    for name in ("supplier_subscription", "grid_subscription"):
        site["dated_components"].append(
            {**deepcopy(site["dated_components"][0]), "id": name, "unit": "DKK/month", "amount": 50}
        )
    validate_site(site)
    value, parts = compose_dated(slot, tariff_for(site))
    assert value == original and len(parts["fixed_subscriptions_excluded"]) == 2
