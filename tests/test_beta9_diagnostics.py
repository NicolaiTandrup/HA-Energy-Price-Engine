"""Beta.9 native completion and stored, fail-closed device presentation."""

import json
from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.charging_diagnostics import charging_readiness
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.device_diagnostics import (
    COMPONENTS,
    availability,
    stored_breakdown,
    technical_entity,
)
from custom_components.ha_energy_price_engine.sensor import ComponentSensor, DisplaySensor

from .test_beta8_dashboard import export_frontend
from .test_integration import model, price_service, setup  # noqa: F401


def entity_id(hass, unique):
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "home_" + unique)


@pytest.mark.usefixtures("price_service")
async def test_activation_boundary_native_states_restart_history_and_api(hass, freezer):
    freezer.move_to("2026-10-30T18:07:00Z")  # Local19:07, next19:15.
    data = model()
    data["pricing_start"] = "2026-10-30T18:15:00+00:00"
    entry = await setup(hass, data)
    c = entry.runtime_data
    start = dt_util.parse_datetime(data["pricing_start"])
    current = start - timedelta(minutes=15)
    api = get_api(hass)
    assert str(api.lookup("home", current, start).status) == "INCOMPLETE"
    assert str(api.lookup("home", start, start + timedelta(minutes=15)).status) == "READY"
    assert availability(c)["code"] == "waiting_first_quarter"
    assert availability(c, "history")["code"] == "historical_gap"
    assert availability(c, "tomorrow")["code"] == "ready"
    assert DisplaySensor(c, "current").native_value is None
    assert stored_breakdown(c)["period"] == "next_quarter"
    assert hass.states.get(entity_id(hass, "breakdown_period")).state == "next_quarter"
    from custom_components.ha_energy_price_engine.dashboard import price_schedule

    await export_frontend(hass, "activation", price_schedule(c))
    text = await charging_readiness(hass, entry)
    assert "19:15" in text and "current quarter began before" in text
    assert "next quarter is Ready" in text and "Full-day statistics require" in text
    assert hass.states.get(entity_id(hass, "display_current_ore")).state == "unknown"
    activation_state = hass.states.get(entity_id(hass, "prices_start_at"))
    assert activation_state.state == "2026-10-30T19:15+01:00"
    assert "state_class" not in activation_state.attributes
    before = tuple(c.price_engine.records["home"])
    freezer.move_to("2026-10-30T18:15:00Z")
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "current_availability")).state == "ready"
    assert hass.states.get(entity_id(hass, "breakdown_period")).state == "current_quarter"
    assert float(hass.states.get(entity_id(hass, "display_current_ore")).state) == pytest.approx(
        41.625
    )
    assert availability(c, "history")["code"] == "historical_gap"
    await export_frontend(hass, "activated", price_schedule(c))
    assert tuple(c.price_engine.records["home"]) == before
    assert not api.lookup("home", current, start).records  # Never backfilled.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert availability(entry.runtime_data)["code"] == "ready"
    assert not get_api(hass).lookup("home", current, start).records
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
@pytest.mark.parametrize("vat_included", [False, True])
async def test_eight_applied_values_and_mixed_vat_without_reads_io(hass, freezer, vat_included):
    freezer.move_to("2026-10-30T18:00:00Z")
    data = model()
    data["dated_components"][0]["vat_included"] = vat_included
    entry = await setup(hass, data)
    c = entry.runtime_data
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
                    side_effect=AssertionError("device read IO/recomposition"),
                )
            )
        for _ in range(20):
            snapshot = stored_breakdown(c)
            for key in COMPONENTS:
                sensor = ComponentSensor(c, key)
                assert sensor.native_value == snapshot["components"][key]
                assert sensor.native_unit_of_measurement == "øre/kWh"
                assert sensor.suggested_display_precision == 2
                assert sensor.state_class is None
                attrs = sensor.extra_state_attributes
                assert attrs["verification"] == "verified"
                assert attrs["period"] == "current_quarter" and attrs["source"]
                assert not attrs["subscriptions_included"]
    row = (
        get_api(hass)
        .lookup("home", dt_util.utcnow(), dt_util.utcnow() + timedelta(minutes=15))
        .records[0]
    )
    parts = json.loads(row.components_json)["components"]
    values = snapshot["components"]
    assert set(values) == set(COMPONENTS)
    for key in COMPONENTS[:6]:
        assert values[key] == parts[key]["ex_vat"] * 100
        assert snapshot["component_metadata"][key] == {
            k: v for k, v in parts[key].items() if k not in {"ex_vat", "vat", "incl_vat"}
        }
    assert snapshot["source"] == json.loads(row.source_json)
    assert values["vat"] == sum(p["vat"] for p in parts.values()) * 100
    assert values["final"] == row.final_price_incl_vat * 100
    assert values["final"] == pytest.approx(sum(values[k] for k in COMPONENTS[:-1]))
    assert c.price_engine.database.path.read_bytes() == before
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_explanation_failure_priority_missing_storage_stale_loading_and_publication(
    hass, freezer
):
    freezer.move_to("2026-10-30T18:07:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    reports = c.schedule.days["home"]
    today, tomorrow = "2026-10-30", "2026-10-31"
    report = reports[today]
    original = dict(report)
    report.update(
        status="INCOMPLETE", failure_stage="configuration", missing_components=["supplier"]
    )
    assert availability(c)["code"] == "missing_components"
    assert all(v is None for v in stored_breakdown(c)["components"].values())
    report.update(status="ERROR", failure_stage="storage", missing_components=[])
    assert availability(c)["code"] == "storage_error"
    report.update(failure_stage="source")
    assert availability(c)["code"] == "verification_error"
    report.update(status="STALE")
    assert availability(c)["code"] == "stale"
    report.clear()
    report.update(original)
    c.price_engine.load_errors["home"] = "Recorded storage recovery error"
    assert availability(c)["code"] == "storage_error"
    c.price_engine.load_errors.clear()
    c.price_engine.records["home"] = ()
    c.price_engine.index["home"] = ()
    reports.clear()
    c.price_updater.raw_reports.clear()
    assert availability(c)["code"] == "loading"
    reports[tomorrow] = {"status": "INCOMPLETE", "failure_stage": "source"}
    c.price_updater.raw_reports[tomorrow] = {"status": "INCOMPLETE", "valid_slots": 0}
    assert availability(c, "tomorrow")["code"] == "waiting_publication"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_technical_defaults_and_explicit_native_opt_in_out_preserve_registry(hass, freezer):
    freezer.move_to("2026-10-30T18:00:00Z")
    entry = await setup(hass)
    registry = er.async_get(hass)
    technical = [
        e
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        if technical_entity(e.unique_id, "home")
    ]
    assert len(technical) == 9
    assert all(e.disabled_by is er.RegistryEntryDisabler.INTEGRATION for e in technical)
    assert all(
        e.disabled_by is er.RegistryEntryDisabler.INTEGRATION
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        if "estimated" in e.unique_id
    )
    r = await hass.config_entries.options.async_init(entry.entry_id)
    assert "setup_done" in r["menu_options"] and "setup_check" in r["menu_options"]
    fid = r["flow_id"]
    r = await hass.config_entries.options.async_configure(
        fid, {"next_step_id": "diagnostic_entities"}
    )
    assert r["step_id"] == "diagnostic_entities"
    kept = entity_id(hass, "current_price")
    before = tuple(entry.runtime_data.price_engine.records["home"])
    r = await hass.config_entries.options.async_configure(fid, {"technical_entities": [kept]})
    assert r["step_id"] == "setup_review"
    assert registry.async_get(kept).disabled_by is None
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(kept).disabled_by is None
    assert hass.states.get(kept).attributes["state_class"] == "measurement"
    assert tuple(entry.runtime_data.price_engine.records["home"]) == before
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "setup_done"})
    r = await hass.config_entries.options.async_init(entry.entry_id)
    fid = r["flow_id"]
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "diagnostic_entities"})
    await hass.config_entries.options.async_configure(fid, {"technical_entities": []})
    assert registry.async_get(kept).disabled_by is er.RegistryEntryDisabler.USER
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(kept).disabled_by is er.RegistryEntryDisabler.USER
    assert registry.async_get(kept).unique_id == "home_current_price"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_beta8_enabled_custom_entities_are_not_force_disabled(hass, freezer):
    freezer.move_to("2026-10-30T18:00:00Z")
    entry = MockConfigEntry(domain=DOMAIN, data=model(), unique_id="home")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "home_current_price",
        config_entry=entry,
        suggested_object_id="my_custom_canonical",
    )
    registry.async_update_entity(
        old.entity_id, name="My canonical preference", hidden_by=er.RegistryEntryHider.USER
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    kept = registry.async_get(old.entity_id)
    assert kept.entity_id == old.entity_id and kept.name == "My canonical preference"
    assert kept.disabled_by is None and kept.hidden_by is er.RegistryEntryHider.USER
    assert hass.states.get(old.entity_id).attributes["unit_of_measurement"] == "DKK/kWh"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("language", ["en", "da"])
async def test_all_new_native_labels_and_title_case(hass, language):
    t = await async_get_translations(hass, language, "entity", {DOMAIN})
    prefix = f"component.{DOMAIN}.entity.sensor."
    for key in COMPONENTS:
        assert t[prefix + "component_" + key + ".name"]
    assert "next_quarter" in " ".join(t)
    for key in (
        "raw_today",
        "raw_tomorrow",
        "final_status",
        "next_quarter_status",
        "historical_day_status",
        "tomorrow_readiness",
    ):
        for state in ("ready", "incomplete", "stale", "error"):
            assert t[prefix + key + ".state." + state][0].isupper()
