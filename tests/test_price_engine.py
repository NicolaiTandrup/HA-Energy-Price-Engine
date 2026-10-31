"""Precomputed prices, immutable snapshots, DST, atomicity and no-op verification."""

from asyncio import gather
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from custom_components.ha_energy_price_engine.models import PriceSlot
from custom_components.ha_energy_price_engine.price_engine import PriceEngine, day_bounds

from .helpers import NOW, rows, tariff


@pytest.mark.parametrize(
    "day,count", [(date(2026, 3, 29), 92), (date(2026, 10, 24), 96), (date(2026, 10, 25), 100)]
)
async def test_dst_persist_restart_and_no_read_arithmetic(hass, day, count):
    engine = PriceEngine(hass, "test")
    data = rows(day)
    await engine.async_update(
        "home", data, tariff(), {"verified_at": NOW.isoformat()}, NOW - timedelta(days=365)
    )
    restored = PriceEngine(hass, "test")
    await restored.async_load(["home"])
    assert restored.complete_day("home", day)
    with patch(
        "custom_components.ha_energy_price_engine.price_engine.calculate",
        side_effect=AssertionError("read calculation"),
    ):
        result = restored.lookup("home", *day_bounds(day))
        assert len(result) == count
        assert result[0].final_price_incl_vat == pytest.approx(0.31625)


async def test_unchanged_no_composition_or_sql_and_future_only_revisions(hass):
    engine = PriceEngine(hass, "test")
    data = rows()
    first = await engine.async_update("home", data, tariff(), {"verified_at": NOW.isoformat()}, NOW)
    assert first.changed and len(first.verified_starts) == 96
    with (
        patch(
            "custom_components.ha_energy_price_engine.price_engine.calculate",
            side_effect=AssertionError("recalculation"),
        ),
        patch.object(engine.database, "async_commit", side_effect=AssertionError("SQL write")),
    ):
        assert not (
            await engine.async_update(
                "home", data, tariff(), {"verified_at": (NOW + timedelta(hours=1)).isoformat()}, NOW
            )
        ).changed
    later = data[2].start
    changed = [PriceSlot(s.start, s.end, 3) for s in data]
    await engine.async_update(
        "home",
        changed,
        tariff(),
        {"version": "correction", "verified_at": later.isoformat()},
        later,
    )
    result = engine.lookup("home", data[0].start, data[-1].end)
    assert result[0].revision == 1 and result[2].revision == 2
    assert result[0].final_price_incl_vat == pytest.approx(0.31625)
    assert result[2].final_price_incl_vat == pytest.approx(4.19125)
    assert len(engine.audit["home"]) == 94


async def test_invalid_atomic_batch_and_separate_sites(hass):
    engine = PriceEngine(hass, "test")
    data = rows()
    await engine.async_update("home", data, tariff(), {}, NOW)
    with pytest.raises(ValueError):
        await engine.async_update("home", data + data[:1], tariff(), {}, NOW)
    with patch.object(engine.database, "async_commit", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            await engine.async_update("away", data, tariff(), {}, NOW)
    assert not engine.lookup("away", *day_bounds(date(2026, 10, 24)))
    assert engine.complete_day("home", date(2026, 10, 24))


async def test_concurrent_updates_one_commit(hass):
    engine = PriceEngine(hass, "concurrent")
    args = ("home", rows(), tariff(), {}, NOW)
    results = await gather(engine.async_update(*args), engine.async_update(*args))
    assert [r.changed for r in results] == [True, False]
