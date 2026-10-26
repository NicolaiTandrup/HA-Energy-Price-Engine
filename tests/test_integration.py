"""Real HA lifecycle, independent sites and lookup-only producer/consumer contract."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import SupportsResponse
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_integration,
)

from custom_components.ha_energy_price_engine.api import EngineNotReady, Status, get_api
from custom_components.ha_energy_price_engine.const import DOMAIN, PRICE_REVISION_EVENT
from custom_components.ha_energy_price_engine.diagnostics import async_get_config_entry_diagnostics
from custom_components.ha_energy_price_engine.price_engine import day_bounds

from .test_price_components import rule
from .test_price_engine import rows


def model(site_id="home"):
    return {
        "id": site_id,
        "name": f"Test {site_id}",
        "area": "DK2",
        "timezone": "Europe/Copenhagen",
        "nordpool_entry": "np",
        "vat": 0.25,
        "dso_mode": "manual",
        "danish_public_rates": True,
        "dated_components": [
            rule("supplier", 11, source="Fictional test supplier", locked=True),
            rule("dso", 20, source="Fictional test grid", locked=True),
        ],
    }


@pytest.fixture
async def price_service(hass):
    price = {"amount": -100, "partial": False}

    async def prices(call):
        day = date.fromisoformat(call.data["date"])
        data = rows(day)
        return {
            "DK2": [
                {"start": s.start.isoformat(), "end": s.end.isoformat(), "price": price["amount"]}
                for s in (data[:1] if price["partial"] else data)
            ]
        }

    # Dependency services are mocked; this is not a live Nord Pool/HA connection.
    mock_integration(hass, MockModule("nordpool"))
    hass.services.async_register(
        "nordpool", "get_prices_for_date", prices, supports_response=SupportsResponse.ONLY
    )
    yield price


async def setup(hass, data=None):
    entry = MockConfigEntry(domain=DOMAIN, data=data or model(), unique_id=(data or model())["id"])
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_native_lifecycle_multiple_sites_and_immutable_api(hass, freezer, price_service):
    freezer.move_to("2026-10-23T12:00:00Z")
    home = await setup(hass)
    away_data = model("away")
    away_data["dated_components"][0]["amount"] = 22
    away = await setup(hass, away_data)
    api = get_api(hass)
    assert {s.site_id for s in api.sites()} == {"home", "away"}
    start, end = day_bounds(date(2026, 10, 24))
    with (
        patch(
            "custom_components.ha_energy_price_engine.price_engine.calculate",
            side_effect=AssertionError("read arithmetic"),
        ),
        patch.object(
            home.runtime_data.price_updater, "refresh", side_effect=AssertionError("read HTTP")
        ),
    ):
        result = api.lookup("home", start, end)
        assert result.status == Status.READY and len(result.records) == 96
        assert result.records[0].final_price_incl_vat == pytest.approx(
            (-0.1 + 0.2 + 0.043 + 0.072 + 0.008 + 0.11) * 1.25
        )
        assert (
            api.lookup("away", start, end).records[0].final_price_incl_vat
            > result.records[0].final_price_incl_vat
        )
        with pytest.raises(FrozenInstanceError):
            result.records[0].revision = 100
    assert await hass.config_entries.async_unload(home.entry_id)
    assert api.lookup("home", start, end).status == Status.NOT_LOADED
    assert api.lookup("away", start, end).status == Status.READY
    assert await hass.config_entries.async_unload(away.entry_id)
    with pytest.raises(EngineNotReady):
        get_api(hass)
    with pytest.raises(ValueError, match="version"):
        get_api(hass, 2)


async def test_events_only_when_future_final_prices_change(hass, freezer, price_service):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    events = []
    hass.bus.async_listen(PRICE_REVISION_EVENT, lambda event: events.append(event.data))
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    day = date(2026, 10, 24)
    await c.schedule.refresh_day(c.site, day, now)
    await hass.async_block_till_done()
    assert not events
    price_service["amount"] = 200
    await c.schedule.refresh_day(c.site, day, now)
    await hass.async_block_till_done()
    assert len(events) == 1 and len(events[0]["affected_slots"]) == 96
    assert events[0]["api_version"] == 1
    price_service["partial"] = True
    await c.schedule.refresh_day(c.site, day, now)
    await hass.async_block_till_done()
    result = get_api(hass).lookup("home", *day_bounds(day))
    assert result.status == Status.INCOMPLETE
    assert len(result.records) == 96  # Last verified snapshot retained, readiness degraded.
    assert len(events) == 1
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_redacted_diagnostics_and_source_failure(hass, freezer, price_service):
    from homeassistant.exceptions import HomeAssistantError

    freezer.move_to("2026-10-23T12:00:00Z")
    data = model()
    data["name"] = "PRIVATE ADDRESS"
    data["dated_components"][0]["source"] = "PRIVATE CUSTOMER NUMBER"
    entry = await setup(hass, data)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert "PRIVATE" not in str(diag)
    assert diag["current_components"]["supplier"]["incl_vat"] == pytest.approx(0.1375)
    c = entry.runtime_data
    c.price_updater.official.cache.clear()
    with patch(
        "homeassistant.core.ServiceRegistry.async_call",
        side_effect=HomeAssistantError("offline"),
    ):
        await c.schedule.refresh_day(
            c.site, date(2026, 10, 24), datetime(2026, 10, 23, 12, tzinfo=UTC)
        )
    result = get_api(hass).lookup("home", *day_bounds(date(2026, 10, 24)))
    assert result.status in {Status.ERROR, Status.INCOMPLETE, Status.STALE}
    assert result.records  # Durable data never becomes a fabricated zero.
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_api_validation_stale_history_and_consumer_backoff(hass, freezer, price_service):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    api = get_api(hass)
    start, end = day_bounds(date(2026, 10, 24))
    with pytest.raises(ValueError):
        api.lookup("home", start.replace(tzinfo=None), end)
    with pytest.raises(ValueError):
        api.lookup("home", start + timedelta(seconds=1), end)
    assert api.lookup("unknown", start, end).status == Status.NOT_LOADED
    entry.runtime_data.schedule.days["home"]["2026-10-24"]["last_success"] = "2026-10-20T12:00:00Z"
    assert api.lookup("home", start, end).status == Status.STALE
    assert api.lookup("home", start, end, now=end + timedelta(days=10)).status == Status.READY
    # A consumer ranks stored totals, earliest UTC slot wins ties; no supplier logic.
    result = api.lookup("home", start, end, now=end + timedelta(days=10))
    ranked = sorted(result.records, key=lambda r: (r.final_price_incl_vat, r.start))
    assert ranked[0].start == start
    assert await hass.config_entries.async_unload(entry.entry_id)
