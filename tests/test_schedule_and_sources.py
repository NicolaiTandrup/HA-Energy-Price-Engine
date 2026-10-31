"""Official-only source checks, coalesced reads and required local refresh boundaries."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState

from custom_components.ha_energy_price_engine.api import Status, get_api
from custom_components.ha_energy_price_engine.price_engine import day_bounds
from custom_components.ha_energy_price_engine.prices import OfficialPrices, parse_prices

from .helpers import model
from .test_integration import setup


@pytest.mark.parametrize(
    "bad",
    [
        {"start": "2026-10-24T00:00:00", "end": "2026-10-24T00:15:00", "price": 1},
        {"start": "2026-10-24T00:00:00Z", "end": "2026-10-24T01:00:00Z", "price": 1},
        {"start": "2026-10-24T00:00:00Z", "end": "2026-10-24T00:15:00Z", "price": True},
        {"start": "2026-10-24T00:00:00Z", "end": "2026-10-24T00:15:00Z", "price": float("nan")},
    ],
)
def test_official_normalization_rejects_ambiguous_rows(bad):
    with pytest.raises((ValueError, TypeError)):
        parse_prices([bad])


async def test_source_cache_attempt_backoff_invalidation_and_shadowing(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:00:00Z")
    source = OfficialPrices(hass)
    now = datetime.now(UTC)
    day = date(2026, 10, 24)
    data = await source.get(model(), now, dates=[day])
    assert data[0].price == -0.1
    assert price_service["calls"][-1] == {
        "config_entry": "np",
        "date": str(day),
        "areas": ["DK2"],
        "currency": "DKK",
    }
    for _ in range(10):
        assert await source.get(model(), now, dates=[day]) == data
    assert len(price_service["calls"]) == 1
    source.invalidated.update(source.cache)
    await source.get(model(), now + timedelta(minutes=5), dates=[day])
    assert len(price_service["calls"]) == 1
    await source.get(model(), now + timedelta(minutes=15), dates=[day])
    assert len(price_service["calls"]) == 2
    from types import SimpleNamespace

    with patch(
        "homeassistant.loader.async_get_integration",
        AsyncMock(return_value=SimpleNamespace(is_built_in=False)),
    ):
        with pytest.raises(ValueError, match="shadows"):
            await source.get(model(), now, dates=[day])


async def test_provider_unload_and_event_coalescing(hass, freezer, price_service):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    before = len(price_service["calls"])
    for _ in range(20):
        c._source_changed(None)
    assert c.pending is not None
    assert len(price_service["calls"]) == before
    provider = hass.config_entries.async_get_entry("np")
    provider.mock_state(hass, ConfigEntryState.NOT_LOADED)
    c._provider_state_changed()
    assert get_api(hass).lookup("home", *day_bounds(date(2026, 10, 25))).status == Status.STALE
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert c.stopped and c.pending is None


@pytest.mark.parametrize(
    "local_time,day,complete,expected",
    [
        ("00:01", 24, True, 1),
        ("13:05", 25, True, 1),
        ("13:20", 25, True, 0),
        ("13:20", 25, False, 1),
        ("13:40", 25, False, 1),
        ("23:59", 25, False, 1),
    ],
)
async def test_required_refreshes_and_conditional_retries(
    hass, freezer, price_service, local_time, day, complete, expected
):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    hour, minute = map(int, local_time.split(":"))
    from zoneinfo import ZoneInfo

    now = datetime(2026, 10, 24, hour, minute, tzinfo=ZoneInfo("Europe/Copenhagen")).astimezone(UTC)
    with (
        patch.object(c.schedule, "complete", return_value=complete),
        patch.object(c.schedule, "refresh_day", AsyncMock(return_value=False)) as refresh,
    ):
        await c.schedule.run(now, hour, minute)
        assert refresh.call_count == expected
        if expected:
            assert refresh.call_args.args[1] == date(2026, 10, day)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_source_failure_does_not_publish_retained_rows_as_ready(hass, freezer, price_service):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    before = c.price_engine.records["home"]
    price_service["failure"] = True
    await c.schedule.refresh_day(c.site, date(2026, 10, 25), datetime.now(UTC))
    assert c.price_engine.records["home"] == before
    result = get_api(hass).lookup("home", *day_bounds(date(2026, 10, 25)))
    assert result.status == Status.ERROR and result.slots == ()
    assert c.schedule.days["home"]["2026-10-25"]["failure_stage"] == "source"
    assert await hass.config_entries.async_unload(entry.entry_id)
