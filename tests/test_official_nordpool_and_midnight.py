"""Actual official HA service/schema with mocked market client; native midnight status."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import SupportsResponse
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.price_engine import PriceEngine
from custom_components.ha_energy_price_engine.price_update import PriceUpdater
from custom_components.ha_energy_price_engine.sensor import PriceSensor, ReadinessSensor

from .test_integration import model, price_service, setup  # noqa: F401
from .test_price_engine import rows


@pytest.mark.parametrize(
    "day,count", [(date(2026, 3, 29), 92), (date(2026, 10, 24), 96), (date(2026, 10, 25), 100)]
)
async def test_actual_official_nordpool_service_contract(hass, freezer, day, count):
    from homeassistant.components.nordpool.services import async_setup_services

    freezer.move_to("2026-10-23T12:00:00Z")
    data = rows(day)
    client = AsyncMock()
    client.async_get_delivery_period.return_value = SimpleNamespace(
        entries=[SimpleNamespace(start=s.start, end=s.end, entry={"DK2": -100}) for s in data]
    )
    source = MockConfigEntry(
        domain="nordpool", data={"areas": ["DK2"], "currency": "DKK"}, state=ConfigEntryState.LOADED
    )
    source.add_to_hass(hass)
    source.runtime_data = SimpleNamespace(client=client)
    async_setup_services(hass)
    site = {**model(), "nordpool_entry": source.entry_id}
    engine = PriceEngine(hass, "official-service")
    updater = PriceUpdater(hass, engine)
    assert await updater.refresh(
        site, datetime(2026, 10, 23, 12, tzinfo=UTC), force=True, dates=[day]
    )
    actual = engine.records["home"]
    assert len(actual) == count
    assert actual[0].final_price_incl_vat == pytest.approx(
        (-0.1 + 0.2 + 0.043 + 0.072 + 0.008 + 0.11) * 1.25
    )
    assert client.async_get_delivery_period.call_args.args[1].value == "DKK"
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_midnight_readiness_does_not_keep_yesterdays_ready_label(hass, freezer):
    freezer.move_to("2026-10-23T21:59:00Z")

    async def publication(call):
        day = date.fromisoformat(call.data["date"])
        selected = rows(day) if day == date(2026, 10, 23) else rows(day)[:1]
        return {
            "DK2": [
                {"start": s.start.isoformat(), "end": s.end.isoformat(), "price": 100}
                for s in selected
            ]
        }

    hass.services.async_register(
        "nordpool", "get_prices_for_date", publication, supports_response=SupportsResponse.ONLY
    )
    entry = await setup(hass)
    readiness = ReadinessSensor(entry.runtime_data)
    assert readiness.native_value == "READY"
    freezer.move_to("2026-10-23T22:00:10Z")  # Before the required 00:01 routine.
    assert readiness.native_value == "INCOMPLETE"
    assert PriceSensor(entry.runtime_data).native_value is None
    assert readiness.extra_state_attributes["requested_date"] == "2026-10-24"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_sensor_freshness_tracks_api_without_a_fetch(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    entry.runtime_data.schedule.days["home"]["2026-10-23"]["last_success"] = "2026-10-20T12:00:00Z"
    assert ReadinessSensor(entry.runtime_data).native_value == "STALE"
    assert PriceSensor(entry.runtime_data).native_value is None
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_provider_late_start_and_new_entities_recover_without_waiting_for_publication(
    hass, freezer
):
    from homeassistant.helpers import entity_registry as er
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(domain="nordpool", entry_id="np", state=ConfigEntryState.SETUP_RETRY)
    source.add_to_hass(hass)
    entry = await setup(hass)
    assert entry.runtime_data.data["status"] == "ERROR"
    source.mock_state(hass, ConfigEntryState.LOADED)
    registry = er.async_get(hass)
    entity = registry.async_get_or_create("sensor", "nordpool", "late-source", config_entry=source)
    await hass.async_block_till_done()
    assert entity.entity_id in entry.runtime_data.source_entities
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert entry.runtime_data.data["status"] == "READY"
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)
    await hass.async_block_till_done()
    assert ReadinessSensor(entry.runtime_data).native_value == "STALE"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "fault", ["partial", "duplicate", "overlap", "shifted", "hourly", "nonfinite"]
)
async def test_real_official_service_malformed_intervals_never_publish(hass, freezer, fault):
    from homeassistant.components.nordpool.services import async_setup_services

    freezer.move_to("2026-10-23T12:00:00Z")
    day = date(2026, 10, 24)
    series = [SimpleNamespace(start=s.start, end=s.end, entry={"DK2": 100}) for s in rows(day)]
    if fault == "partial":
        series.pop(5)
    elif fault == "duplicate":
        series.append(series[0])
    elif fault == "overlap":
        series[1].start -= timedelta(minutes=15)
    elif fault == "shifted":
        for s in series:
            s.start += timedelta(minutes=1)
            s.end += timedelta(minutes=1)
    elif fault == "hourly":
        series = [
            SimpleNamespace(start=s.start, end=s.start + timedelta(hours=1), entry=s.entry)
            for s in series[::4]
        ]
    else:
        series[0].entry["DK2"] = float("nan")
    client = AsyncMock()
    client.async_get_delivery_period.return_value = SimpleNamespace(entries=series)
    source = MockConfigEntry(domain="nordpool", state=ConfigEntryState.LOADED)
    source.add_to_hass(hass)
    source.runtime_data = SimpleNamespace(client=client)
    async_setup_services(hass)
    engine = PriceEngine(hass, "malformed-official")
    updater = PriceUpdater(hass, engine)
    assert not await updater.refresh(
        {**model(), "nordpool_entry": source.entry_id},
        datetime(2026, 10, 23, 12, tzinfo=UTC),
        force=True,
        dates=[day],
    )
    assert not engine.records.get("home")
    assert updater.status["home"]["status"] in {"ERROR", "INCOMPLETE"}
    assert not updater.status["home"].get("last_success")
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)
