"""Future windows are independent of absent history; all reads use stored indexes."""

import json
import sqlite3
import zlib
from contextlib import ExitStack, closing
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.charging_cost import estimate_charging_cost
from custom_components.ha_energy_price_engine.models import PriceSlot
from custom_components.ha_energy_price_engine.price_engine import PriceEngine, day_bounds
from custom_components.ha_energy_price_engine.sensor import (
    FinalStatusSensor,
    HistoricalCoverageSensor,
    NextReadinessSensor,
)
from custom_components.ha_energy_price_engine.status import readiness_snapshot, source_status

from .test_beta6_diagnostics import charging_site, recorded_grid
from .test_integration import model, price_service, setup  # noqa: F401


@pytest.mark.parametrize("day,count", [("2026-10-24", 96), ("2026-10-25", 100), ("2026-03-29", 92)])
@pytest.mark.usefixtures("price_service")
async def test_late_activation_current_next_and_midnight_ready_without_backfill(
    hass, freezer, day, count
):
    first, last = day_bounds(date.fromisoformat(day))
    activation = last - timedelta(minutes=105)
    freezer.move_to(activation + timedelta(minutes=5))
    site = charging_site()
    site["pricing_start"] = activation.isoformat()
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get",
        side_effect=recorded_grid,
    ):
        entry = await setup(hass, site)
    c = entry.runtime_data
    api = get_api(hass)
    end = last + timedelta(hours=2)
    snapshot = readiness_snapshot(hass, entry, start=activation, end=end)
    assert (
        snapshot["current"]["status"]
        == snapshot["next"]["status"]
        == snapshot["requested"]["status"]
        == "READY"
    )
    assert snapshot["history_today"]["status"] == "INCOMPLETE"
    assert (
        snapshot["history_today"]["valid_slots"] == 7
        and snapshot["history_today"]["expected_slots"] == count
    )
    assert (
        snapshot["history_tomorrow"]["status"] == "READY" and snapshot["missing_before_activation"]
    )
    assert FinalStatusSensor(c).native_value == NextReadinessSensor(c).native_value == "ready"
    assert HistoricalCoverageSensor(c).native_value == "incomplete"
    assert (
        source_status(c)["health"] == "READY"
        and source_status(c)["historical_day_status"] == "INCOMPLETE"
    )
    original = c.price_engine.records["home"]
    path = c.price_engine.database.path
    before = path.read_bytes()
    with ExitStack() as guards:
        for target in (
            "price_engine.calculate",
            "price_components.compose_dated",
            "prices.OfficialPrices.get",
            "tariff_source.TariffSource.get",
            "ledger.LedgerDatabase._connect",
        ):
            guards.enter_context(
                patch(
                    "custom_components.ha_energy_price_engine." + target,
                    side_effect=AssertionError("consumer fetched/recomposed/wrote"),
                )
            )
        for _ in range(250):
            result = api.lookup("home", activation, end)
            assert (
                str(result.status) == "READY" and result.valid_slots == result.expected_slots == 15
            )
        cost = estimate_charging_cost(api, "home", [(activation, "1.2345")], energy_kind="planned")
        assert cost["price_status"] == "READY"
        assert cost["quarters"][0]["price_dkk_per_kwh"] == original[0].final_price_incl_vat
    assert path.read_bytes() == before
    assert not c.price_engine.lookup("home", first, activation)
    # The actual persisted schema has a primary-key range index and complete provenance.
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM prices WHERE site=? AND start>=? AND start<? ORDER BY start",
            ("home", activation.isoformat(), end.isoformat()),
        ).fetchall()
        assert any("SEARCH" in row[-1] and "INDEX" in row[-1] for row in plan)
        raw = connection.execute(
            "SELECT p.start,p.end,p.amount,p.revision,b.body,s.body FROM prices p JOIN blobs b ON p.components=b.digest JOIN blobs s ON p.source=s.digest ORDER BY p.start LIMIT 1"
        ).fetchone()
        assert datetime.fromisoformat(raw[0]).utcoffset() == timedelta(0)
        assert datetime.fromisoformat(raw[1]) - datetime.fromisoformat(raw[0]) == timedelta(
            minutes=15
        )
        assert raw[2] == original[0].final_price_incl_vat and raw[3] == original[0].revision
        parts = json.loads(zlib.decompress(raw[4]))["components"]
        source = json.loads(zlib.decompress(raw[5]))
        assert parts["spot"]["ex_vat"] == -0.1 and parts["dso"]["ex_vat"] >= 0
        assert source["input_unit"] == "DKK/MWh" and source["verified_at"]
    freezer.move_to(last - timedelta(minutes=5))
    assert NextReadinessSensor(c).native_value == "ready"
    assert readiness_snapshot(hass, entry)["next"]["start"] == last.isoformat()
    restored = PriceEngine(hass, entry.entry_id)
    await restored.async_load(["home"])
    assert restored.records["home"] == original
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_horizon_form_and_missing_future_fail_closed(hass, freezer):
    freezer.move_to("2026-10-27T21:20:00Z")
    data = model()
    data["pricing_start"] = "2026-10-27T21:15:00+00:00"
    entry = await setup(hass, data)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "horizon"}
    )
    fid = result["flow_id"]
    start = "2026-10-27T21:15:00+00:00"
    end = "2026-10-27T23:30:00+00:00"
    good = await hass.config_entries.options.async_configure(fid, {"start": start, "end": end})
    assert "Requested future window: Ready" in good["description_placeholders"]["result"]
    assert "Today’s full-day history: Incomplete" in good["description_placeholders"]["result"]
    wrong = await hass.config_entries.options.async_configure(
        fid, {"start": "2026-10-27T21:45:00+00:00", "end": "2026-10-27T21:30:00+00:00"}
    )
    assert wrong["errors"] == {"end": "invalid_horizon"}
    missing = await hass.config_entries.options.async_configure(
        fid, {"start": start, "end": "2026-10-29T01:00:00+00:00"}
    )
    assert "Requested future window: Incomplete" in missing["description_placeholders"]["result"]
    assert (
        missing["data_schema"]({"start": start, "end": "2026-10-29T01:00:00+00:00"})["start"]
        == start
    )
    before = entry.runtime_data.price_engine.records["home"]
    c = entry.runtime_data
    c.schedule.days["home"]["2026-10-28"]["status"] = "ERROR"
    assert (
        readiness_snapshot(
            hass, entry, start=datetime.fromisoformat(start), end=datetime.fromisoformat(end)
        )["requested"]["status"]
        == "ERROR"
    )
    assert c.price_engine.records["home"] == before
    hass.config_entries.options.async_abort(fid)
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_changed_quarter_only_updates_affected_future_row(hass, freezer):
    freezer.move_to("2026-10-27T12:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    before = c.price_engine.records["home"]
    now = datetime(2026, 10, 27, 12, 7, tzinfo=UTC)
    start = datetime(2026, 10, 27, 13, tzinfo=UTC)
    row = next(r for r in before if r.start == start)
    tariff = c.price_updater.component_inputs["2026-10-27"]["tariff"]
    source = c.price_updater.component_inputs["2026-10-27"]["source"]
    changed = []
    for raw in c.price_updater.raw_slots["2026-10-27"]:
        changed.append(
            PriceSlot(raw.start, raw.end, 0.123456789 if raw.start == start else raw.price)
        )
    original_commit = c.price_engine.database.async_commit
    with patch.object(c.price_engine.database, "async_commit", wraps=original_commit) as commit:
        assert await c.price_engine.async_update("home", changed, tariff, source, now)
        written = commit.call_args.args[1]
        assert len(written) == 1 and written[0]["start"] == start.isoformat()
    after = c.price_engine.records["home"]
    assert [a for a, b in zip(after, before, strict=True) if a != b] == [
        next(r for r in after if r.start == start)
    ]
    assert get_api(hass).lookup_revision("home", start, row.revision) == row
    assert all(a == b for a, b in zip(after, before, strict=True) if a.start < now)
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_missing_tomorrow_component_does_not_invalidate_current_quarter(hass, freezer):
    freezer.move_to("2026-10-27T21:20:00Z")
    site = model()
    site["pricing_start"] = "2026-10-27T21:15:00+00:00"
    site["dated_components"][0]["valid_to"] = "2026-10-28"
    entry = await setup(hass, site)
    snapshot = readiness_snapshot(
        hass,
        entry,
        start=datetime(2026, 10, 27, 21, 15, tzinfo=UTC),
        end=datetime(2026, 10, 27, 23, 30, tzinfo=UTC),
    )
    assert snapshot["current"]["status"] == snapshot["next"]["status"] == "READY"
    assert snapshot["requested"]["status"] == "INCOMPLETE"
    assert (
        snapshot["requested"]["valid_slots"] == 7 and snapshot["requested"]["expected_slots"] == 9
    )
    assert snapshot["history_tomorrow"]["valid_slots"] == 0
    freezer.move_to("2026-10-27T22:55:00Z")
    assert NextReadinessSensor(entry.runtime_data).native_value == "incomplete"
    assert NextReadinessSensor(entry.runtime_data).extra_state_attributes["health"] == "INCOMPLETE"
    assert (
        HistoricalCoverageSensor(entry.runtime_data).extra_state_attributes["health"]
        == "INCOMPLETE"
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_current_next_radius_transition_keeps_cost_precision(hass, freezer, price_service):  # noqa: F811
    from custom_components.ha_energy_price_engine.charging_diagnostics import charging_breakdown
    from custom_components.ha_energy_price_engine.sensor import NextPriceSensor, PriceSensor

    freezer.move_to("2026-10-27T15:50:00Z")  # 16:45 normal quarter, then17:00 peakCET
    price_service["amount"] = 100
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get",
        side_effect=recorded_grid,
    ):
        entry = await setup(hass, charging_site())
    c = entry.runtime_data
    assert PriceSensor(c).native_value == pytest.approx(0.683155)
    assert NextPriceSensor(c).native_value == pytest.approx(1.47946625)
    first = datetime(2026, 10, 27, 15, 45, tzinfo=UTC)
    for start, shown in [(first, "68.32"), (first + timedelta(minutes=15), "147.95")]:
        text = await charging_breakdown(hass, entry, start)
        assert shown + " øre/kWh" in text
    result = estimate_charging_cost(
        get_api(hass),
        "home",
        [(first, "1.25"), (first + timedelta(minutes=15), "2.0")],
        energy_kind="planned",
    )
    assert float(result["estimated_cost_dkk"]) == pytest.approx(3.81287625, abs=1e-12)
    assert float(result["estimated_cost_dkk"]) != 0.6832 * 1.25 + 1.4795 * 2
    assert await hass.config_entries.async_unload(entry.entry_id)
