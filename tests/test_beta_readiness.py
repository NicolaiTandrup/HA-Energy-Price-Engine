"""Beta regressions: verification is source time, not lookup or refresh time."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.price_engine import PriceEngine, day_bounds
from custom_components.ha_energy_price_engine.price_schedule import PriceSchedule

from .test_price_engine import rows


async def context(hass, now, verified):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    site = {"id": "home", "name": "Home", "area": "DK2", "timezone": "Europe/Copenhagen"}
    engine = PriceEngine(hass, entry.entry_id)
    await engine.async_update("home", rows(date(2026, 10, 24)), {"mode": "all_in"}, {}, now)
    c = SimpleNamespace(
        hass=hass,
        entry=entry,
        site=site,
        sites={"home": SimpleNamespace(site=site)},
        price_engine=engine,
        price_updater=SimpleNamespace(
            refresh=AsyncMock(return_value=False),
            status={"home": {"status": "READY", "last_success": verified, "source_slots": 96}},
        ),
        async_request_refresh=AsyncMock(),
    )
    c.schedule = PriceSchedule(c)
    hass.data[DOMAIN] = {entry.entry_id: c}
    return c


async def test_cached_verification_never_promoted_to_now(hass):
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    verified = (now - timedelta(hours=2)).isoformat()
    c = await context(hass, now, verified)
    await c.schedule.refresh_day(c.site, date(2026, 10, 24), now)
    assert c.schedule.days["home"]["2026-10-24"]["last_success"] == verified


async def test_failed_unchanged_refresh_still_updates_readiness_entities(hass):
    now = datetime(2026, 10, 23, 11, 5, tzinfo=UTC)
    c = await context(hass, now, now.isoformat())
    c.price_updater.status["home"] = {"status": "ERROR", "reason": "offline"}
    await c.schedule.run(now, 13, 5)
    c.async_request_refresh.assert_awaited_once()


@pytest.mark.parametrize("verified", ["not-a-date", "2026-10-23T12:00:00", "2026-10-25T00:00:00Z"])
async def test_invalid_or_future_verification_fails_closed(hass, verified):
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    c = await context(hass, now, verified)
    c.schedule.days = {"home": {"2026-10-24": {"status": "READY", "last_success": verified}}}
    result = get_api(hass).lookup("home", *day_bounds(date(2026, 10, 24)), now=now)
    assert str(result.status) == "ERROR"


async def test_api_identity_and_machine_contract(hass):
    from custom_components.ha_energy_price_engine.api import serialize_result

    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    c = await context(hass, now, now.isoformat())
    await c.schedule.refresh_day(c.site, date(2026, 10, 24), now)
    api = get_api(hass)
    assert api.sites()[0].producer_entry_id == c.entry.entry_id
    result = api.lookup(
        "home", *day_bounds(date(2026, 10, 24)), now=now, producer_entry_id=c.entry.entry_id
    )
    payload = serialize_result(result)
    assert payload["producer_entry_id"] == c.entry.entry_id
    assert payload["vat_included"] is True and len(payload["slots"]) == 96
    assert payload["verified_at"] == now.isoformat()
    assert (
        str(
            api.lookup(
                "home", *day_bounds(date(2026, 10, 24)), now=now, producer_entry_id="wrong"
            ).status
        )
        == "NOT_LOADED"
    )


@pytest.mark.parametrize("version", [True, 1.0, "1", 2])
async def test_version_is_an_actual_supported_integer(hass, version):
    with pytest.raises(ValueError):
        get_api(hass, version)


async def test_exact_published_revision_remains_recoverable_after_future_correction(hass):
    from unittest.mock import patch

    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    c = await context(hass, now, now.isoformat())
    original = c.price_engine.records["home"][0]
    await c.price_engine.async_update(
        "home",
        rows(date(2026, 10, 24)),
        {"mode": "spot_ex_vat", "vat": 0.25},
        {"version": "correction"},
        now,
    )
    api = get_api(hass)
    with patch(
        "custom_components.ha_energy_price_engine.price_engine.calculate",
        side_effect=AssertionError("accounting read recalculation"),
    ):
        assert api.lookup_revision("home", original.start, original.revision) == original
        assert api.lookup_revision("home", original.start, 999) is None
        assert api.lookup_revision("wrong_site", original.start, original.revision) is None
        assert (
            api.lookup_revision(
                "home", original.start, original.revision, producer_entry_id="wrong"
            )
            is None
        )
