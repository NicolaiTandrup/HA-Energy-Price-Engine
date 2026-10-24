"""Actual Radius C rows, metadata conventions, outages and date boundaries."""

import json
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from custom_components.ha_energy_price_engine.price_engine import day_bounds
from custom_components.ha_energy_price_engine.tariff_source import (
    RADIUS_CODE,
    RADIUS_GLN,
    TariffSource,
    normalize_tariffs,
)

DATA = json.loads((Path(__file__).parent / "fixtures/radius_c_datahub.json").read_text())


@pytest.mark.parametrize(
    "day,count,high,peak",
    [
        (date(2026, 4, 2), 96, 19.90775, 51.76025),
        (date(2026, 10, 24), 96, 39.8155, 119.446625),
        (date(2026, 10, 25), 100, 39.8155, 119.446625),
        (date(2026, 3, 29), 92, 36.6125, 109.85),
    ],
)
def test_verified_rates_and_effective_seasons(day, count, high, peak):
    from zoneinfo import ZoneInfo

    slots, metadata = normalize_tariffs(DATA, RADIUS_GLN, RADIUS_CODE, *day_bounds(day))
    assert len(slots) == count
    by_hour = {s.start.astimezone(ZoneInfo("Europe/Copenhagen")).hour: s.price * 125 for s in slots}
    assert by_hour[6] == pytest.approx(high)
    assert by_hour[17] == pytest.approx(peak)
    assert metadata["vat_included"] is False and metadata["unit"] == "DKK/kWh"


@pytest.mark.parametrize(
    "change",
    [
        {"ChargeTypeCode": "other"},
        {"ChargeType": "D01"},
        {"GLN_Number": "wrong"},
        {"Price1": -1},
        {"Price1": None},
    ],
)
def test_invalid_identity_and_amounts_rejected(change):
    data = deepcopy(DATA)
    data[0].update(change)
    with pytest.raises((ValueError, TypeError)):
        normalize_tariffs(data, RADIUS_GLN, RADIUS_CODE, *day_bounds(date(2026, 10, 24)))


async def test_cache_fetch_once_and_offline_restart(hass, aiohttp_client):
    from unittest.mock import patch

    source = TariffSource(hass, "test")
    # Test real response plumbing via HA's HTTP mock library rather than live API.
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.async_get_clientsession"
    ) as session:

        class Response:
            def raise_for_status(self):
                pass

            async def json(self):
                return {"records": DATA}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        session.return_value.get.return_value = Response()
        now = datetime(2026, 10, 23, 12, tzinfo=UTC)
        args = ({"dso_mode": "radius_c"}, *day_bounds(date(2026, 10, 24)), now)
        first, meta = await source.get(*args)
        await source.get(*args)
        assert session.return_value.get.call_count == 1
        restored = TariffSource(hass, "test")
        await restored.load()
        assert (await restored.get(*args))[0] == first
        assert session.return_value.get.call_count == 1


async def test_cached_schedule_survives_outage_with_warning(hass):
    from unittest.mock import patch

    from aiohttp import ClientError

    source = TariffSource(hass, "outage")
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    key = RADIUS_GLN + ":" + RADIUS_CODE
    source.cache[key] = {"records": DATA, "fetched_at": now.isoformat()}
    from datetime import timedelta

    tomorrow = now + timedelta(days=1)
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.async_get_clientsession"
    ) as session:
        session.return_value.get.side_effect = ClientError("offline")
        slots, metadata = await source.get(
            {"dso_mode": "radius_c"}, *day_bounds(date(2026, 10, 25)), tomorrow
        )
        assert len(slots) == 100 and metadata["warning"]
        await source.get(
            {"dso_mode": "radius_c"},
            *day_bounds(date(2026, 10, 25)),
            tomorrow + timedelta(minutes=5),
        )
        assert session.return_value.get.call_count == 1


async def test_midnight_cache_does_not_skip_new_morning_publication(hass):
    from unittest.mock import patch

    source = TariffSource(hass, "publication")
    # 00:01 Copenhagen on Oct 23 belongs to the previous publication bucket.
    source.cache[RADIUS_GLN + ":" + RADIUS_CODE] = {
        "records": DATA,
        "fetched_at": "2026-10-22T22:01:00+00:00",
    }

    class Response:
        def raise_for_status(self):
            pass

        async def json(self):
            return {"records": DATA}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.async_get_clientsession"
    ) as session:
        session.return_value.get.return_value = Response()
        now = datetime(2026, 10, 23, 11, 5, tzinfo=UTC)
        args = ({"dso_mode": "radius_c"}, *day_bounds(date(2026, 10, 24)), now)
        await source.get(*args)
        await source.get(*args)
        assert session.return_value.get.call_count == 1
