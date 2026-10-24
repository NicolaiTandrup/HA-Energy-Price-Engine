"""Future-only edits, failures, schedule recovery and upstream parity boundaries."""

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.ha_energy_price_engine.configuration import (
    household_historical_example,
    tariff_for,
)
from custom_components.ha_energy_price_engine.const import PRICE_REVISION_EVENT
from custom_components.ha_energy_price_engine.price_components import compose_dated
from custom_components.ha_energy_price_engine.price_engine import PriceEngine, day_bounds
from custom_components.ha_energy_price_engine.prices import OfficialPrices

from .test_integration import model, price_service, setup  # noqa: F401
from .test_price_engine import rows


@pytest.mark.usefixtures("price_service")
async def test_offline_targeted_reconfigure_atomic_audit_and_no_historical_mutation(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    old_site = deepcopy(c.site)
    original = c.price_engine.records["home"]
    old_rate = c.site["dated_components"][0]
    new_rate = {**old_rate, "amount": 33, "valid_from": "2026-10-24"}
    old_rate["valid_to"] = "2026-10-24"
    c.site["dated_components"].append(new_rate)
    events = []
    hass.bus.async_listen(PRICE_REVISION_EVENT, lambda event: events.append(event.data))
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    with patch(
        "homeassistant.core.ServiceRegistry.async_call", side_effect=AssertionError("edit HTTP")
    ):
        assert await c.reconfigure(old_site, now)
        assert not await c.reconfigure(deepcopy(c.site), now)
    await hass.async_block_till_done()
    assert len(events) == 1 and len(events[0]["affected_slots"]) == 96
    threshold = day_bounds(date(2026, 10, 24))[0]
    current = c.price_engine.records["home"]
    assert [r for r in current if r.start < now] == [r for r in original if r.start < now]
    assert [r.final_price_incl_vat for r in current if r.start < threshold] == [
        r.final_price_incl_vat for r in original if r.start < threshold
    ]
    assert all(
        r.final_price_incl_vat == pytest.approx(original[-1].final_price_incl_vat + 0.275)
        for r in current
        if r.start >= threshold
    )
    restored = PriceEngine(hass, entry.entry_id)
    await restored.async_load(["home"])
    assert restored.records["home"] == current and len(restored.audit["home"]) == len(
        [r for r in original if r.start >= now]
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_reconfigure_disk_failure_is_atomic_and_past_only_edits_do_not_calculate(
    hass, freezer
):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    before = c.price_engine.records["home"]
    old_site = deepcopy(c.site)
    c.site["dated_components"][0]["amount"] = 44
    with patch(
        "custom_components.ha_energy_price_engine.ledger.LedgerDatabase.async_commit",
        side_effect=OSError("disk full"),
    ):
        with pytest.raises(OSError):
            await c.reconfigure(old_site, datetime(2026, 10, 23, 12, tzinfo=UTC))
    assert c.price_engine.records["home"] == before
    assert c.price_engine.audit.get("home", []) == []
    c.site = deepcopy(old_site)
    previous = deepcopy(c.site)
    c.site["dated_components"].append(
        {
            **c.site["dated_components"][0],
            "valid_from": "2025-01-01",
            "valid_to": "2026-01-01",
            "amount": 99,
        }
    )
    with patch(
        "custom_components.ha_energy_price_engine.price_engine.calculate",
        side_effect=AssertionError("unaffected recalc"),
    ):
        assert not await c.reconfigure(previous, datetime(2026, 10, 23, 12, tzinfo=UTC))
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "day,valid",
    [
        (date(2026, 5, 31), False),
        (date(2026, 6, 1), True),
        (date(2026, 9, 30), True),
        (date(2026, 10, 1), False),
        (date(2027, 6, 1), False),
    ],
)
def test_ewii_household_terms_never_extrapolate(day, valid):
    site = model()
    site["dated_components"][0] = household_historical_example()
    start, _ = day_bounds(day)
    from custom_components.ha_energy_price_engine.models import PriceSlot

    slot = PriceSlot(start, start + timedelta(minutes=15), -0.1)
    if valid:
        total, parts = compose_dated(slot, tariff_for(site))
        assert parts["components"]["supplier"]["ex_vat"] == 0.030
        assert total == pytest.approx((-0.1 + 0.2 + 0.043 + 0.072 + 0.008 + 0.030) * 1.25)
    else:
        with pytest.raises(ValueError, match="Missing verified"):
            compose_dated(slot, tariff_for(site))


async def test_per_day_signatures_survive_restart_and_do_not_recompose_on_midnight_check(hass):
    engine = PriceEngine(hass, "signatures")
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    for day in (date(2026, 10, 23), date(2026, 10, 24)):
        await engine.async_update("home", rows(day), {"mode": "all_in"}, {}, now)
    restored = PriceEngine(hass, "signatures")
    await restored.async_load(["home"])
    with patch(
        "custom_components.ha_energy_price_engine.price_engine.calculate",
        side_effect=AssertionError("unchanged day"),
    ):
        assert not await restored.async_update(
            "home", rows(date(2026, 10, 24)), {"mode": "all_in"}, {}, now + timedelta(hours=10)
        )
        assert not await restored.async_update(
            "home", rows(date(2026, 10, 23)), {"mode": "all_in"}, {}, now + timedelta(hours=10)
        )


@pytest.mark.usefixtures("price_service")
async def test_native_source_event_debounced_and_unload_cancels(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    np_entry = MockConfigEntry(
        domain="nordpool", entry_id="np", data={}, state=ConfigEntryState.LOADED
    )
    np_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    source = registry.async_get_or_create("sensor", "nordpool", "np_source", config_entry=np_entry)
    # Entity registry requires its config entry to exist for a realistic source.
    entry = await setup(hass)
    c = entry.runtime_data
    hass.states.async_set(source.entity_id, "1")
    hass.states.async_set(source.entity_id, "2")
    await hass.async_block_till_done()
    assert c.pending is not None
    with patch.object(c.schedule, "refresh_day", wraps=c.schedule.refresh_day) as verify:
        freezer.tick(timedelta(seconds=61))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert verify.await_count == 2  # One coalesced current/next check.
        assert all(call.kwargs["force"] is False for call in verify.call_args_list)
    hass.states.async_set(source.entity_id, "3")
    await hass.async_block_till_done()
    assert c.pending is not None
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert c.pending is None


@pytest.mark.usefixtures("price_service")
async def test_nordpool_attempt_backoff_keeps_error_until_verified_recovery(hass):
    source = OfficialPrices(hass)
    site = model()
    day = date(2026, 10, 24)
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    await source.get(site, now, compose=False, dates=[day])
    source.invalidated.update(source.cache)
    with patch(
        "homeassistant.core.ServiceRegistry.async_call", side_effect=HomeAssistantError("offline")
    ) as call:
        # Within the backoff period the cached verified input is retained.
        assert await source.get(site, now + timedelta(seconds=61), compose=False, dates=[day])
        call.assert_not_awaited()
        assert await source.get(site, now + timedelta(minutes=16), compose=False, dates=[day])
        assert source.last_errors == [str(day)]
        assert await source.get(site, now + timedelta(minutes=17), compose=False, dates=[day])
        assert source.last_errors == [str(day)]
        assert call.await_count == 1
    await source.get(site, now + timedelta(minutes=32), compose=False, dates=[day])
    assert not source.last_errors


async def test_permanent_history_and_corrupt_ledger_reported(hass):
    engine = PriceEngine(hass, "history")
    past = date(2020, 1, 1)
    await engine.async_update(
        "home", rows(past), {"mode": "all_in"}, {}, datetime(2026, 10, 24, tzinfo=UTC)
    )
    assert len(engine.lookup("home", *day_bounds(past))) == 96
    await engine.store("broken").async_save({"records": [{"invalid": True}], "revision": 1})
    await engine.async_load(["broken"])
    assert engine.load_errors["broken"] and not engine.records["broken"]


@pytest.mark.usefixtures("price_service")
@pytest.mark.parametrize("mode", ["automatic", "locked", "fallback", "missing"])
async def test_native_dso_verification_manual_lock_and_no_zero_fallback(hass, freezer, mode):
    import json
    from pathlib import Path
    from unittest.mock import AsyncMock

    from custom_components.ha_energy_price_engine.diagnostics import (
        async_get_config_entry_diagnostics,
    )
    from custom_components.ha_energy_price_engine.tariff_source import (
        RADIUS_CODE,
        RADIUS_GLN,
        normalize_tariffs,
    )

    freezer.move_to("2026-10-23T12:00:00Z")
    data = model()
    data["dso_mode"] = "radius_c"
    if mode in {"automatic", "missing"}:
        data["dated_components"] = [r for r in data["dated_components"] if r["id"] != "dso"]
    if mode == "fallback":
        data["dated_components"][1]["locked"] = False
        data["dso_manual_fallback"] = True
    records = json.loads((Path(__file__).parent / "fixtures/radius_c_datahub.json").read_text())

    async def grid(site, start, end, now):
        if mode in {"fallback", "missing"}:
            raise ValueError("No sufficiently recent verified tariff cache")
        return normalize_tariffs(records, RADIUS_GLN, RADIUS_CODE, start, end)

    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get",
        new_callable=AsyncMock,
        side_effect=grid,
    ) as fetch:
        entry = await setup(hass, data)
        c = entry.runtime_data
        if mode == "locked":
            fetch.assert_not_awaited()
        else:
            assert fetch.await_count == 2
        rows_today = c.price_engine.lookup("home", *day_bounds(date(2026, 10, 23)))
        if mode == "missing":
            assert not rows_today and c.data["status"] == "ERROR"
        else:
            assert rows_today
            if mode == "fallback":
                assert c.data["status"] == "STALE"
            diag = await async_get_config_entry_diagnostics(hass, entry)
            dso = diag["current_components"]["dso"]["ex_vat"]
            assert dso == pytest.approx(0.318524 if mode == "automatic" else 0.2)
        assert await hass.config_entries.async_unload(entry.entry_id)
