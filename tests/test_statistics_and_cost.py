"""Daily schedule statistics, quarter boundaries and consumer variable cost semantics."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.charging_cost import estimate_charging_cost
from custom_components.ha_energy_price_engine.configuration import current_rate
from custom_components.ha_energy_price_engine.status import price, source_value, statistics

from .helpers import model
from .test_integration import setup


@pytest.mark.parametrize(
    "instant,count",
    [("2026-03-29T12:07:00Z", 92), ("2026-10-24T12:07:00Z", 96), ("2026-10-25T12:07:00Z", 100)],
)
async def test_daily_stats_include_every_past_and_future_quarter_immediately(
    hass, freezer, price_service, instant, count
):
    freezer.move_to(instant)
    entry = await setup(hass)
    facts = statistics(entry.runtime_data)
    assert facts["scope"] == "full_day" and facts["used_slots"] == facts["day_slots"] == count
    assert facts["average"] == facts["minimum"] == facts["maximum"] == pytest.approx(0.31625)
    assert source_value(entry.runtime_data, "current_spot") == -0.1
    assert source_value(entry.runtime_data, "next_spot") == -0.1
    assert price(entry.runtime_data).slots[0].price == pytest.approx(0.31625)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_from_now_stats_no_invented_history_or_skipped_middle_gap(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    now = datetime.now(UTC)
    data = current_rate(model(), "supplier", "3", False, now)
    entry = await setup(hass, data)
    c = entry.runtime_data
    facts = statistics(c)
    assert facts["scope"] == "remaining_day" and facts["used_slots"] == 39
    assert all(r.start >= now for r in c.price_engine.records["home"])
    day = c.schedule.days["home"]["2026-10-24"]
    day["verified_starts"].remove("2026-10-24T17:00:00+00:00")
    assert statistics(c)["scope"] == "unavailable"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_cost_uses_api_v2_full_precision_negative_prices_and_missing_never_zero(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    price_service["amount"] = -1000
    entry = await setup(hass)
    api = get_api(hass, 2)
    first = datetime(2026, 10, 24, 13, tzinfo=UTC)
    with (
        patch.object(
            entry.runtime_data.price_updater.official,
            "get",
            side_effect=AssertionError("cost fetch"),
        ),
        patch(
            "custom_components.ha_energy_price_engine.price_engine.calculate",
            side_effect=AssertionError("cost arithmetic"),
        ),
    ):
        value = estimate_charging_cost(
            api,
            "home",
            [(first, "1.2345"), (first + timedelta(minutes=15), "0")],
            energy_kind="planned",
        )
    assert float(value["estimated_cost_dkk"]) == pytest.approx(
        1.2345 * (-1 + 0.2 + 0.03 + 0.043 + 0.072 + 0.008) * 1.25
    )
    assert len(value["quarters"]) == 2 and value["quarters"][0]["revision"] > 0
    entry.runtime_data.settings_current = False
    value = estimate_charging_cost(api, "home", [(first, "0")], energy_kind="planned")
    assert value["estimated_cost_dkk"] is None and not value["quarters"]
    assert await hass.config_entries.async_unload(entry.entry_id)
