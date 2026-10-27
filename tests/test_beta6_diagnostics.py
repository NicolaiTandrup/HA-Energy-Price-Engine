"""Recorded Radius TOU, canonical quarter arithmetic and read-only energy costing."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.charging_cost import estimate_charging_cost
from custom_components.ha_energy_price_engine.charging_diagnostics import (
    charging_breakdown,
    quarter_choices,
)
from custom_components.ha_energy_price_engine.component_status import component_snapshot
from custom_components.ha_energy_price_engine.price_engine import day_bounds
from custom_components.ha_energy_price_engine.tariff_source import (
    RADIUS_CODE,
    RADIUS_GLN,
    normalize_tariffs,
)

from .test_integration import model, price_service, setup  # noqa: F401
from .test_tariff_source import DATA


async def recorded_grid(site, start, end, now):
    slots, source = normalize_tariffs(DATA, RADIUS_GLN, RADIUS_CODE, start, end)
    return slots, {**source, "fetched_at": now.isoformat()}


def charging_site():
    data = model()
    data["dso_mode"] = "radius_c"
    data["dated_components"] = [r for r in data["dated_components"] if r["id"] != "dso"]
    data["dated_components"][0].update(amount="0.5", unit="ore/kWh", vat_included=False)
    return data


@pytest.mark.parametrize("day,count", [("2026-10-24", 96), ("2026-10-25", 100), ("2026-03-29", 92)])
@pytest.mark.usefixtures("price_service")
async def test_each_future_quarter_uses_its_own_recorded_grid_band(hass, freezer, day, count):
    freezer.move_to(day + "T10:00:00Z")
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get",
        side_effect=recorded_grid,
    ):
        entry = await setup(hass, charging_site())
    start, end = day_bounds(date.fromisoformat(day))
    records = get_api(hass).lookup("home", start, end).records
    grids, _ = normalize_tariffs(DATA, RADIUS_GLN, RADIUS_CODE, start, end)
    assert len(records) == len(grids) == count
    assert len({g.price for g in grids}) >= 3
    with (
        patch(
            "custom_components.ha_energy_price_engine.component_status.resolved_rules",
            side_effect=AssertionError("UI rule recomposition"),
        ),
        patch(
            "custom_components.ha_energy_price_engine.price_engine.calculate",
            side_effect=AssertionError("UI price calculation"),
        ),
    ):
        for record, grid in zip(records, grids, strict=True):
            parts = json.loads(record.components_json)["components"]
            assert parts["dso"]["ex_vat"] == grid.price
            assert record.final_price_incl_vat == pytest.approx(
                (-0.1 + grid.price + 0.005 + 0.043 + 0.072 + 0.008) * 1.25
            )
            snapshot = component_snapshot(hass, entry, reference=record.start)
            assert snapshot["components"]["dso"]["value"] == pytest.approx(grid.price * 100)
            assert snapshot["components"]["supplier"]["value"] == pytest.approx(0.5)
            assert snapshot["components"]["final"]["value"] == record.final_price_incl_vat * 100
        text = await charging_breakdown(hass, entry, records[-1].start)
        assert "including VAT" in text and "Fixed subscriptions are excluded" in text
    choices = quarter_choices(hass, entry)
    assert len(choices) >= count
    labels = [label for _, label in choices]
    if count == 100:
        assert "2026-10-25T02:00+02:00" in labels and "2026-10-25T02:00+01:00" in labels
    elif count == 92:
        assert not any(label.startswith("2026-03-29T02:") for label in labels)
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_session_energy_cost_across_peak_transition_is_not_invoice_or_planning(hass, freezer):
    freezer.move_to("2026-10-24T10:00:00Z")
    data = charging_site()
    data["dated_components"].append(
        {
            **data["dated_components"][0],
            "id": "supplier_subscription",
            "unit": "DKK/month",
            "amount": 999,
        }
    )
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get",
        side_effect=recorded_grid,
    ):
        entry = await setup(hass, data)
    start = datetime(2026, 10, 24, 14, 45, tzinfo=UTC)  # 16:45 CEST, then17:00 peak
    before = entry.runtime_data.price_engine.records["home"]
    allocations = [(start, "1,25"), (start + timedelta(minutes=15), "2.0")]
    for kind in ("planned", "measured"):
        report = estimate_charging_cost(
            get_api(hass),
            "home",
            allocations,
            energy_kind=kind,
            now=start + timedelta(minutes=31) if kind == "measured" else None,
        )
        assert report["price_status"] == "READY"
        assert report["energy_kind"] == kind and not report["is_settled_accounting"]
        assert Decimal(report["estimated_cost_dkk"]) == pytest.approx(Decimal("3.00037625"))
        assert report["energy_kwh"] == "3.25" and not report["fixed_subscriptions_included"]
        assert len({q["price_dkk_per_kwh"] for q in report["quarters"]}) == 2
    assert entry.runtime_data.price_engine.records["home"] == before
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get",
        side_effect=ValueError("Recorded tariff verification unavailable"),
    ):
        await entry.runtime_data.schedule.startup()
    stale = estimate_charging_cost(get_api(hass), "home", allocations, energy_kind="planned")
    assert stale["price_status"] in {"STALE", "ERROR"} and stale["estimated_cost_dkk"] is None
    snapshot = component_snapshot(hass, entry, reference=start)
    assert snapshot["components"]["final"]["status"] == "stale"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "kind,allocations",
    [
        ("planned", []),
        ("measured", [(datetime(2099, 1, 1, tzinfo=UTC), "1")]),
        ("unknown", [(datetime(2026, 10, 24, tzinfo=UTC), "1")]),
        ("measured", [(datetime(2026, 10, 24, tzinfo=UTC), "-1")]),
        ("planned", [(datetime(2026, 10, 24, 0, 1, tzinfo=UTC), "1")]),
        (
            "measured",
            [
                (datetime(2026, 10, 24, tzinfo=UTC), "1"),
                (datetime(2026, 10, 24, 0, 30, tzinfo=UTC), "2"),
            ],
        ),
    ],
)
def test_missing_invalid_or_unallocated_energy_never_becomes_zero(kind, allocations):
    with pytest.raises(ValueError):
        estimate_charging_cost(None, "home", allocations, energy_kind=kind)


@pytest.mark.usefixtures("price_service")
async def test_recorded_season_version_changes_at_local_midnight(hass, freezer):
    freezer.move_to("2026-09-30T20:00:00Z")
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get",
        side_effect=recorded_grid,
    ):
        entry = await setup(hass, charging_site())
    start = datetime(2026, 9, 30, 21, 45, tzinfo=UTC)  # 23:45 local, then October1 midnight
    end = start + timedelta(minutes=30)
    result = get_api(hass).lookup("home", start, end)
    assert str(result.status) == "READY" and len(result.records) == 2
    grids, source = normalize_tariffs(DATA, RADIUS_GLN, RADIUS_CODE, start, end)
    assert len(source["effective_versions"]) == 2
    for row, grid in zip(result.records, grids, strict=True):
        assert json.loads(row.components_json)["components"]["dso"]["ex_vat"] == grid.price
    assert (
        json.loads(result.records[0].source_json)["dso"]["version"]
        != json.loads(result.records[1].source_json)["dso"]["version"]
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_approved_estimate_overrides_stale_ui_record_but_not_authoritative_history(
    hass, freezer
):
    from custom_components.ha_energy_price_engine import apply_settings
    from custom_components.ha_energy_price_engine.charging_cost import estimate_charging_cost
    from custom_components.ha_energy_price_engine.configuration import settings
    from custom_components.ha_energy_price_engine.contracts import current_contract

    freezer.move_to("2026-10-27T12:07:00Z")
    entry = await setup(hass)
    old = entry.runtime_data.price_engine.records["home"]
    site = current_contract(
        settings(entry),
        "0.5",
        False,
        None,
        True,
        datetime(2026, 10, 27, 12, 7, tzinfo=UTC),
        source="Explicit fictional visual estimate",
    )
    assert await apply_settings(hass, entry, site)
    point = datetime(2026, 10, 27, 12, 15, tzinfo=UTC)
    snapshot = component_snapshot(hass, entry, reference=point)
    assert snapshot["components"]["supplier"]["value"] == pytest.approx(0.5)
    assert snapshot["components"]["final"]["status"] == "provisional"
    assert snapshot["api_status"] == "INCOMPLETE"
    assert entry.runtime_data.price_engine.records["home"] == old
    cost = estimate_charging_cost(get_api(hass), "home", [(point, "1")], energy_kind="planned")
    assert cost["estimated_cost_dkk"] is None
    assert await hass.config_entries.async_unload(entry.entry_id)
