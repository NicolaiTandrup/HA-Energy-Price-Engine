"""Bounded real HA frontend transport over immutable applied price snapshots."""

import json
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.auth.permissions import PolicyPermissions
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.dashboard import CARD_URL, price_schedule
from custom_components.ha_energy_price_engine.price_engine import day_bounds

from .test_beta6_diagnostics import charging_site, recorded_grid
from .test_integration import model, setup
from .test_integration import price_service as _price_service
from .test_provisional import provisional

price_service = _price_service


@pytest.mark.parametrize("day,count", [("2026-10-24", 96), ("2026-10-25", 100), ("2026-03-29", 92)])
@pytest.mark.usefixtures("price_service")
async def test_schedule_dst_components_totals_tariff_ranges_and_no_io(hass, freezer, day, count):
    freezer.move_to(day + "T10:07:00Z")
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get",
        side_effect=recorded_grid,
    ):
        entry = await setup(hass, charging_site())
    c = entry.runtime_data
    records = c.price_engine.records["home"]
    before = c.price_engine.database.path.read_bytes()
    with ExitStack() as guards:
        for target in (
            "price_engine.calculate",
            "price_components.compose_dated",
            "component_status.resolved_rules",
            "prices.OfficialPrices.get",
            "tariff_source.TariffSource.get",
            "ledger.LedgerDatabase._connect",
        ):
            guards.enter_context(
                patch(
                    "custom_components.ha_energy_price_engine." + target,
                    side_effect=AssertionError("dashboard IO/arithmetic"),
                )
            )
        for _ in range(25):
            data = price_schedule(c)
    today = data["days"][0]
    assert today["date"] == day and len(today["slots"]) == count
    assert today["expected_slots"] == today["ready_slots"] == count
    assert data["unit"] == "øre/kWh" and data["schema_version"] == 1
    assert len(json.dumps(data)) < 200_000  # Bounded WS response, not Recorder attributes.
    assert sum(len(d["slots"]) for d in data["days"]) <= 200
    original = {r.start.isoformat(): r for r in records}
    for row in today["slots"]:
        r = original[row["start"]]
        parts = json.loads(r.components_json)["components"]
        for name in (
            "spot",
            "dso",
            "energinet_net",
            "energinet_system",
            "supplier",
            "electricity_tax",
        ):
            assert row[name] == parts[name]["ex_vat"] * 100
        assert row["vat"] == sum(p["vat"] for p in parts.values()) * 100
        assert row["final"] == r.final_price_incl_vat * 100
        assert row["final"] == pytest.approx(
            sum(
                row[k]
                for k in (
                    "spot",
                    "dso",
                    "energinet_net",
                    "energinet_system",
                    "supplier",
                    "electricity_tax",
                    "vat",
                )
            )
        )
        assert row["spot"] < 0 and row["status"] == row["raw_status"] == "READY"
        evidence = data["provenance"][row["provenance"]]
        assert evidence["components"] == {
            k: {n: v for n, v in p.items() if n not in {"ex_vat", "vat", "incl_vat"}}
            for k, p in parts.items()
        }
        assert evidence["source"] == json.loads(r.source_json)
        assert row["revision"] == r.revision
    tariffs = data["dso_today"]
    assert len(tariffs) == 4
    assert tariffs[0]["start"] == today["start"] and tariffs[-1]["end"] == today["end"]
    assert all(a["end"] == b["start"] for a, b in zip(tariffs, tariffs[1:]))
    assert (
        sum(
            (dt_util.parse_datetime(t["end"]) - dt_util.parse_datetime(t["start"])).total_seconds()
            / 900
            for t in tariffs
        )
        == count
    )
    assert len({r["value"] for r in tariffs}) == 3
    for row in today["slots"]:
        group = next(t for t in tariffs if t["start"] <= row["start"] < t["end"])
        assert (
            group["value"] == row["dso"]
            and group["status"] == row["status"]
            and group["source"] == "DatahubPricelist"
        )
    if count == 100:
        assert {r["local_start"] for r in today["slots"]} >= {
            "2026-10-25T02:00+02:00",
            "2026-10-25T02:00+01:00",
        }
    elif count == 92:
        assert not any(r["local_start"].startswith(day + "T02:") for r in today["slots"])
    assert (
        c.price_engine.records["home"] == records
        and c.price_engine.database.path.read_bytes() == before
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_missing_supplier_and_provisional_keep_raw_graph_but_never_final(hass, freezer):
    freezer.move_to("2026-10-30T10:07:00Z")
    data = model()
    data["dated_components"] = [r for r in data["dated_components"] if r["id"] != "supplier"]
    data["provisional_supplier"] = provisional()
    entry = await setup(hass, data)
    view = price_schedule(entry.runtime_data)
    for day in view["days"]:
        assert day["ready_slots"] == 0 and day["raw_ready_slots"] == 96
        assert day["missing_components"] == ["supplier"]
        assert day["required_action"] and day["reason"]
        assert all(
            r["spot"] == -10
            and r["raw_status"] == "READY"
            and r["final"] is None
            and r["supplier"] is None
            and r["vat"] is None
            for r in day["slots"]
        )
    assert len(view["dso_today"]) == 1 and view["dso_today"][0]["value"] is None
    assert view["provenance"] == {} and not entry.runtime_data.price_engine.records.get("home")
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_missing_tomorrow_rate_and_late_activation_keep_current_ready(hass, freezer):
    freezer.move_to("2026-10-30T21:20:00Z")
    data = model()
    data["pricing_start"] = "2026-10-30T21:15:00+00:00"
    data["dated_components"][0]["valid_to"] = "2026-10-31"
    entry = await setup(hass, data)
    view = price_schedule(entry.runtime_data)
    assert view["current"]["status"] == view["next"]["status"] == "READY"
    assert view["days"][0]["status"] == "INCOMPLETE" and view["days"][0]["ready_slots"] == 7
    assert view["days"][1]["ready_slots"] == 0 and view["days"][1]["raw_ready_slots"] == 96
    assert all(r["final"] is None for r in view["days"][0]["slots"][:-7])
    assert view["dso_today"][0]["value"] is None and len(view["dso_today"]) == 2
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_unpublished_tomorrow_and_failed_refresh_never_graph_retained_final(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-30T10:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    before = c.price_engine.records["home"]
    price_service["partial"] = True
    tomorrow = date(2026, 10, 31)
    await c.schedule.refresh_day(c.site, tomorrow, dt_util.utcnow(), force=True)
    view = price_schedule(c)
    assert view["current"]["status"] == "READY"
    assert view["days"][1]["ready_slots"] == 0 and view["days"][1]["raw_ready_slots"] == 1
    assert all(
        r["final"] is None and r["stored_final"] is not None for r in view["days"][1]["slots"]
    )
    assert c.price_engine.records["home"] == before
    c.schedule.days["home"][str(tomorrow)].update(
        status="ERROR", reason="Verified source unavailable"
    )
    view = price_schedule(c)
    assert all(r["status"] == "ERROR" and r["final"] is None for r in view["days"][1]["slots"])
    assert view["days"][1]["reason"] == "Verified source unavailable"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_verified_revision_updates_data_preserving_past_and_canonical_api(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-30T10:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    before = price_schedule(c)
    old = c.price_engine.records["home"]
    price_service["amount"] = 234.567
    await c.schedule.refresh_day(c.site, date(2026, 10, 31), dt_util.utcnow(), force=True)
    after = price_schedule(c)
    assert after["revision"] > before["revision"]
    assert after["days"][0]["slots"] == before["days"][0]["slots"]
    new = after["days"][1]["slots"][0]
    assert new["revision"] > before["days"][1]["slots"][0]["revision"]
    api = get_api(hass).lookup("home", *day_bounds(date(2026, 10, 31)))
    assert new["spot"] == pytest.approx(23.4567)
    assert new["final"] == api.records[0].final_price_incl_vat * 100
    assert get_api(hass).lookup_revision("home", old[-1].start, old[-1].revision) == old[-1]
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_native_authenticated_websocket_permissions_multi_site_and_unload(
    hass, freezer, hass_ws_client, hass_admin_user
):
    freezer.move_to("2026-10-30T10:07:00Z")
    home = await setup(hass)
    away = await setup(hass, model("away"))
    registry = er.async_get(hass)
    entity = registry.async_get_entity_id("sensor", DOMAIN, "home_current_price")
    other = registry.async_get_entity_id("sensor", DOMAIN, "away_current_price")
    refresh = await hass.auth.async_create_refresh_token(
        hass_admin_user, client_id="http://localhost"
    )
    token = hass.auth.async_create_access_token(refresh)
    client = await hass_ws_client(hass, access_token=token)
    await client.send_json(
        {"id": 1, "type": "ha_energy_price_engine/price_schedule", "entity_id": entity}
    )
    reply = await client.receive_json()
    assert reply["success"] and reply["result"]["site"]["id"] == "home"
    assert len(reply["result"]["days"]) == 2
    await client.send_json(
        {"id": 2, "type": "ha_energy_price_engine/price_schedule", "entity_id": "sensor.unrelated"}
    )
    assert (await client.receive_json())["error"]["code"] == "not_found"
    # Use HA's actual permission evaluation, not a transport-specific allow-all.
    hass_admin_user.permissions = PolicyPermissions(
        {"entities": {"entity_ids": {entity: {"read": True}}}}, None
    )
    await client.send_json(
        {"id": 3, "type": "ha_energy_price_engine/price_schedule", "entity_id": other}
    )
    assert (await client.receive_json())["error"]["code"] == "unauthorized"
    await client.send_json(
        {
            "id": 4,
            "type": "ha_energy_price_engine/price_schedule",
            "entity_id": entity,
            "start": "2020-01-01",
        }
    )
    assert not (await client.receive_json())["success"]  # No unbounded export parameters.
    assert await hass.config_entries.async_unload(home.entry_id)
    await client.send_json(
        {"id": 5, "type": "ha_energy_price_engine/price_schedule", "entity_id": entity}
    )
    assert (await client.receive_json())["error"]["code"] == "not_found"
    assert await hass.config_entries.async_unload(away.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_bundled_local_card_served_by_native_http(hass, freezer, hass_client):
    freezer.move_to("2026-10-30T10:07:00Z")
    entry = await setup(hass)
    client = await hass_client()
    response = await client.get(CARD_URL)
    assert response.status == 200
    text = await response.text()
    assert (
        text
        == (
            Path(__file__).parents[1]
            / "custom_components"
            / DOMAIN
            / "www/energy-price-engine-card.js"
        ).read_text()
    )
    assert "ha_energy_price_engine/price_schedule" in text
    assert "https://" not in text and "fetch(" not in text
    assert "ha_energy_price_engine/price_schedule" not in hass.services.async_services().get(
        DOMAIN, {}
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_optional_estimates_new_defaults_and_existing_beta7_registry(hass, freezer):
    freezer.move_to("2026-10-30T10:07:00Z")
    registry = er.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data=model(), unique_id="home")
    entry.add_to_hass(hass)
    ids = []
    for offset in (0, 1):
        item = registry.async_get_or_create(
            "sensor", DOMAIN, f"home_estimated_price_{offset}", config_entry=entry
        )
        ids.append(item.entity_id)
    registry.async_update_entity(ids[1], hidden_by=er.RegistryEntryHider.USER)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(ids[0]).hidden_by is er.RegistryEntryHider.INTEGRATION
    assert registry.async_get(ids[1]).hidden_by is er.RegistryEntryHider.USER
    preferred = registry.async_get_entity_id("sensor", DOMAIN, "home_display_estimated_current_ore")
    assert registry.async_get(preferred).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert not hass.states.get(preferred)
    options = {**entry.data, "provisional_supplier": provisional()}
    hass.config_entries.async_update_entry(entry, options=options)
    await hass.async_block_till_done()
    assert registry.async_get(ids[0]).hidden_by is None
    assert registry.async_get(ids[1]).hidden_by is er.RegistryEntryHider.USER
    assert registry.async_get(preferred).disabled_by is None
    assert registry.async_get(ids[0]).entity_id == ids[0]
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_title_case_localized_statuses_preserve_uppercase_legacy_enum(hass, freezer):
    freezer.move_to("2026-10-30T10:07:00Z")
    entry = await setup(hass)
    translations = await async_get_translations(hass, "en", "entity", {DOMAIN})
    prefix = f"component.{DOMAIN}.entity.sensor."
    for key in ("readiness", "tomorrow_status"):
        assert prefix + key + ".state.READY" not in translations
    for key in (
        "raw_today",
        "raw_tomorrow",
        "final_status",
        "historical_day_status",
        "next_quarter_status",
        "tomorrow_readiness",
    ):
        assert translations[prefix + key + ".state.ready"] == "Ready"
        assert translations[prefix + key + ".state.incomplete"] == "Incomplete"
    entity = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "home_readiness")
    assert hass.states.get(entity).state == "READY"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_single_missing_stored_quarter_is_a_gap_not_a_zero_or_whole_day_failure(
    hass, freezer
):
    freezer.move_to("2026-10-30T10:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    missing = c.price_engine.records["home"][-12]
    records = tuple(r for r in c.price_engine.records["home"] if r.start != missing.start)
    c.price_engine._install(
        "home", records, c.price_engine.signatures["home"], c.price_engine.revisions["home"]
    )
    view = price_schedule(c)
    tomorrow = view["days"][1]
    assert tomorrow["ready_slots"] == 95 and tomorrow["raw_ready_slots"] == 96
    assert tomorrow["status"] == "INCOMPLETE"
    row = next(r for r in tomorrow["slots"] if r["start"] == missing.start.isoformat())
    assert row["final"] is None and row["revision"] is None and row["spot"] == -10
    assert all(r["final"] is not None for r in tomorrow["slots"] if r is not row)
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_expired_raw_verification_and_pending_settings_are_not_ready(hass, freezer):
    freezer.move_to("2026-10-30T10:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    freezer.move_to("2026-10-30T12:08:00Z")
    view = price_schedule(c)
    assert view["current"]["status"] == "READY"  # Canonical API verification policy unchanged.
    assert view["days"][1]["raw_ready_slots"] == 0
    assert all(r["raw_status"] == "STALE" for r in view["days"][1]["slots"])
    assert view["days"][0]["slots"][0]["raw_status"] == "READY"  # Settled history.
    c.settings_current = False
    view = price_schedule(c)
    assert view["current"]["status"] == "STALE"
    assert all(r["final"] is None for r in view["days"][1]["slots"])
    assert await hass.config_entries.async_unload(entry.entry_id)
