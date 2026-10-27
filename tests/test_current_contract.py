"""Current-rate confirmation never invents earlier unverified history."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest

from custom_components.ha_energy_price_engine.api import Status, get_api
from custom_components.ha_energy_price_engine.contracts import current_contract
from custom_components.ha_energy_price_engine.price_engine import day_bounds

from .test_integration import model, price_service, setup  # noqa: F401


@pytest.mark.usefixtures("price_service")
async def test_open_ended_current_rate_starts_next_complete_quarter(hass, freezer):
    freezer.move_to("2026-10-27T16:07:00Z")
    now = datetime(2026, 10, 27, 16, 7, tzinfo=UTC)
    data = current_contract(model(), 11.1, False, 29, False, now, source="Confirmed synthetic bill")
    assert data["pricing_start"] == "2026-10-27T16:15:00+00:00"
    entry = await setup(hass, data)
    c = entry.runtime_data
    records = c.price_engine.records["home"]
    assert min(r.start for r in records) == datetime(2026, 10, 27, 16, 15, tzinfo=UTC)
    assert all(
        r.final_price_incl_vat == pytest.approx((-0.1 + 0.2 + 0.111 + 0.043 + 0.072 + 0.008) * 1.25)
        for r in records
    )
    assert (
        json.loads(records[0].components_json)["fixed_subscriptions_excluded"][0]["incl_vat"]
        == 36.25
    )
    start, end = day_bounds(date(2026, 10, 27))
    assert get_api(hass).lookup("home", start, end).status == Status.INCOMPLETE
    assert (
        get_api(hass).lookup("home", datetime.fromisoformat(data["pricing_start"]), end).status
        == Status.READY
    )
    assert len(get_api(hass).lookup("home", *day_bounds(date(2026, 10, 28))).records) == 96
    assert c.price_updater.raw_reports["2026-10-27"]["valid_slots"] == 96
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert entry.runtime_data.price_engine.records["home"] == records
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_editing_contract_keeps_settled_rows_and_missing_gaps_unfilled(hass, freezer):
    from custom_components.ha_energy_price_engine import apply_settings
    from custom_components.ha_energy_price_engine.configuration import settings

    freezer.move_to("2026-10-27T16:07:00Z")
    entry = await setup(hass)
    before = entry.runtime_data.price_engine.records["home"]
    now = datetime(2026, 10, 27, 16, 7, tzinfo=UTC)
    updated = current_contract(
        settings(entry), 5, True, None, False, now, source="New confirmed synthetic contract"
    )
    assert await apply_settings(hass, entry, updated)
    after = {r.start: r for r in entry.runtime_data.price_engine.records["home"]}
    assert all(after[r.start] == r for r in before if r.start < now)
    assert any(
        after[r.start].final_price_incl_vat != r.final_price_incl_vat
        for r in before
        if r.start >= now + timedelta(minutes=15)
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_current_provisional_is_visual_only_and_not_backfilled(hass, freezer):
    freezer.move_to("2026-10-27T16:07:00Z")
    data = current_contract(
        model(),
        11.1,
        False,
        None,
        True,
        datetime(2026, 10, 27, 16, 7, tzinfo=UTC),
        source="Approved synthetic estimate",
    )
    entry = await setup(hass, data)
    c = entry.runtime_data
    assert not c.price_engine.records.get("home")
    rows = c.price_updater.estimated_slots["2026-10-27"]
    assert rows and rows[0].start == datetime(2026, 10, 27, 16, 15, tzinfo=UTC)
    assert get_api(hass).lookup("home", rows[0].start, rows[-1].end).status == Status.INCOMPLETE
    assert await hass.config_entries.async_unload(entry.entry_id)
