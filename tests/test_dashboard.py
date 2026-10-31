"""Real producer snapshots feed the card tests; DST, raw-only and permission boundaries."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from custom_components.ha_energy_price_engine.configuration import current_rate
from custom_components.ha_energy_price_engine.dashboard import (
    price_schedule,
    websocket_schedule,
    websocket_sites,
)
from custom_components.ha_energy_price_engine.status import statistics

from .helpers import model
from .test_integration import setup


@pytest.mark.parametrize(
    "name,instant,count",
    [
        ("normal", "2026-10-24T12:07:00Z", 96),
        ("fall", "2026-10-25T12:07:00Z", 100),
        ("spring", "2026-03-28T12:07:00Z", 96),
        ("missing", "2026-10-24T12:07:00Z", 96),
        ("unpublished", "2026-10-24T12:07:00Z", 96),
        ("gap", "2026-10-24T12:07:00Z", 96),
        ("varied", "2026-10-24T12:07:00Z", 96),
        ("activation", "2026-10-24T12:07:00Z", 96),
    ],
)
async def test_real_snapshot_export(
    hass, freezer, price_service, radius_source, name, instant, count
):
    freezer.move_to(instant)
    now = datetime.now(UTC)
    day = now.astimezone(__import__("zoneinfo").ZoneInfo("Europe/Copenhagen")).date()
    data = model(dso_mode="radius_c")
    data["dated_components"] = [r for r in data["dated_components"] if r["id"] != "dso"]
    if name == "missing":
        data["dated_components"] = []
    if name == "activation":
        data = current_rate(model(dated_components=[]), "dso", "20", False, now)
        data = current_rate(data, "supplier", "3", False, now)
    if name == "varied":
        data["dated_components"][0]["source"] = '<img src=x onerror="window.PE_XSS=true">'
        price_service["amount"] = -1000
    entry = await setup(hass, data)
    c = entry.runtime_data
    if name == "unpublished":
        price_service["empty"] = True
        await c.schedule.refresh_day(c.site, day + timedelta(days=1), now)
    if name == "gap":
        c.schedule.days["home"][str(day + timedelta(days=1))]["verified_starts"].pop()
    if name == "varied":
        # Explicit zero/negative raw quotes, not manufactured missing prices.
        price_service["amount"] = 0
        await c.schedule.refresh_day(c.site, day + timedelta(days=1), now)
    before = len(price_service["calls"])
    with (
        patch.object(
            c.price_updater.official, "get", side_effect=AssertionError("dashboard fetch")
        ),
        patch.object(
            c.price_engine.database, "async_commit", side_effect=AssertionError("dashboard write")
        ),
        patch(
            "custom_components.ha_energy_price_engine.price_engine.calculate",
            side_effect=AssertionError("dashboard calculation"),
        ),
    ):
        value = price_schedule(c, now)
        assert value["schema_version"] == 2
        assert len(value["days"][0]["slots"]) == count
        assert value["statistics"]["day_slots"] == count
        if name not in {"missing", "activation"}:
            assert value["statistics"]["scope"] == "full_day"
        if name == "activation":
            assert (
                value["statistics"]["scope"] == "remaining_day"
                and value["statistics"]["used_slots"] == 39
            )
            assert value["current"]["status"] == "INCOMPLETE" and value["next"]["status"] == "READY"
        if name == "missing":
            assert all(s["final"] is None for d in value["days"] for s in d["slots"])
            assert value["days"][0]["missing_components"]
    assert len(price_service["calls"]) == before
    if directory := os.environ.get("PE_FRONTEND_FIXTURES"):
        Path(directory).mkdir(parents=True, exist_ok=True)
        (Path(directory) / (name + ".json")).write_text(json.dumps(value))
    if name == "activation" and directory:
        (Path(directory) / "activated.json").write_text(
            json.dumps(price_schedule(c, now.replace(minute=15, second=0, microsecond=0)))
        )
    if name == "normal":
        old = statistics(c)
        assert old["minimum"] < old["average"] < old["maximum"]
        if directory:
            (Path(directory) / "revision-before.json").write_text(json.dumps(value))
        price_service["amount"] = 200
        await c.schedule.refresh_day(c.site, day + timedelta(days=1), now)
        if directory:
            (Path(directory) / "revision-after.json").write_text(json.dumps(price_schedule(c, now)))
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_permission_filtered_autodiscovery_and_multi_site_selection(
    hass, freezer, price_service
):
    from types import SimpleNamespace
    from unittest.mock import Mock

    freezer.move_to("2026-10-24T12:07:00Z")
    one = await setup(hass)
    connection = SimpleNamespace(
        user=SimpleNamespace(permissions=SimpleNamespace(check_entity=Mock(return_value=True))),
        send_result=Mock(),
        send_error=Mock(),
    )
    websocket_sites(hass, connection, {"id": 1})
    assert connection.send_result.call_args.args[1][0]["site_id"] == "home"
    websocket_schedule(hass, connection, {"id": 2})
    assert connection.send_result.call_args.args[1]["site"]["id"] == "home"
    two = await setup(hass, model(id="away", name="Away"))
    websocket_schedule(hass, connection, {"id": 3})
    assert connection.send_error.call_args.args[1] == "select_site"
    websocket_schedule(hass, connection, {"id": 4, "site_id": "away"})
    assert connection.send_result.call_args.args[1]["site"]["id"] == "away"
    connection.user.permissions.check_entity.return_value = False
    websocket_sites(hass, connection, {"id": 5})
    assert connection.send_result.call_args.args[1] == []
    websocket_schedule(hass, connection, {"id": 6, "site_id": "home"})
    assert connection.send_error.call_args.args[1] == "select_site"
    assert await hass.config_entries.async_unload(one.entry_id)
    assert await hass.config_entries.async_unload(two.entry_id)
