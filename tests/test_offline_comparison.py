"""Recorded comparison never requires co-running price brokers or fills gaps."""

from copy import deepcopy
from datetime import datetime

import pytest

from custom_components.ha_energy_price_engine.ledger import export_recorded_range
from tools.compare_recorded_prices import compare

from .test_ledger_recovery import seed

START = "2026-10-24T12:00:00+00:00"
END = "2026-10-24T12:30:00+00:00"


def recorded():
    return {
        "site_id": "legacy-house",
        "currency": "DKK",
        "unit": "DKK/kWh",
        "vat_included": True,
        "slots": [
            {"start": START, "end": "2026-10-24T12:15:00+00:00", "final_price_incl_vat": -0.25},
            {"start": "2026-10-24T12:15:00+00:00", "end": END, "final_price_incl_vat": 0},
        ],
    }


def test_recorded_negative_and_known_zero_are_exact_and_missing_is_not_zero():
    source = recorded()
    candidate = {**deepcopy(source), "site_id": "candidate-house"}
    args = {
        "legacy_site": "legacy-house",
        "candidate_site": "candidate-house",
        "start": START,
        "end": END,
    }
    assert compare(source, candidate, **args)["passed"]
    candidate["slots"].pop()
    result = compare(source, candidate, **args)
    assert not result["passed"] and result["missing_candidate"] == 1
    candidate["slots"][0]["final_price_incl_vat"] = -0.2
    assert compare(source, candidate, **args)["mismatches"] == 1


@pytest.mark.parametrize(
    "change",
    [{"unit": "ore/kWh"}, {"currency": "EUR"}, {"vat_included": False}, {"site_id": "wrong-site"}],
)
def test_unknown_conventions_and_site_mapping_rejected(change):
    source = recorded()
    candidate = {**deepcopy(source), **change}
    with pytest.raises(ValueError):
        compare(
            source,
            candidate,
            legacy_site="legacy-house",
            candidate_site="legacy-house",
            start=START,
            end=END,
        )


async def test_readonly_export_from_verified_backup_for_recorded_comparison(hass, tmp_path):
    engine = await seed(hass)
    backup = tmp_path / "recorded.sqlite3"
    await engine.database.async_backup(backup)
    result = await hass.async_add_executor_job(
        export_recorded_range,
        backup,
        "home",
        datetime.fromisoformat(START),
        datetime.fromisoformat(END),
    )
    assert len(result["slots"]) == 2 and result["slots"][0]["final_price_incl_vat"] == -0.1
    assert result["capture_type"] == "offline_checked_ledger_backup"
    assert "status" not in result  # Historical export is not a claim of current READY.
