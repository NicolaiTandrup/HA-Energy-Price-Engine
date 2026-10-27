"""User-visible native wizard, durable drafts, atomic apply and presentation invariants."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.sensor import DisplaySensor, PriceSensor

from .test_integration import model, price_service, setup  # noqa: F401
from .wizard_helpers import options_review, source_page


@pytest.mark.usefixtures("price_service")
async def test_new_official_wizard_source_defaults_review_save_incomplete(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(
        domain="nordpool",
        title="Official DK2",
        data={"areas": ["DK2"]},
        state=ConfigEntryState.LOADED,
    )
    source.add_to_hass(hass)
    r = await source_page(hass, "Sommerhus")
    fields = {str(k) for k in r["data_schema"].schema}
    assert fields == {"nordpool_entry", "navigation"}
    assert not fields & {"price_entity", "price_unit", "price_basis", "stale_minutes"}
    fid = r["flow_id"]
    r = await hass.config_entries.flow.async_configure(fid, {"nordpool_entry": source.entry_id})
    defaults = {str(k): k.default() for k in r["data_schema"].schema if callable(k.default)}
    assert defaults["area"] == "DK2" and defaults["timezone"] == "Europe/Copenhagen"
    assert defaults["vat_percent"] == 25
    assert hass.config_entries.flow._progress[fid].draft["danish_public_rates"] is True
    r = await hass.config_entries.flow.async_configure(
        fid, {"area": "DK2", "timezone": "Europe/Copenhagen", "vat_percent": 25}
    )
    assert r["step_id"] == "wizard_grid"
    r = await hass.config_entries.flow.async_configure(
        fid, {"dso_mode": "manual", "navigation": "next"}
    )
    r = await hass.config_entries.flow.async_configure(
        fid, {"supplier": "ewii", "add_contract": False}
    )
    r = await hass.config_entries.flow.async_configure(fid, {"danish_public_rates": False})
    r = await hass.config_entries.flow.async_configure(fid, {"display_unit": "øre/kWh"})
    assert r["step_id"] == "wizard_review"
    assert r["menu_options"][0] == "wizard_save"
    assert "✕" in r["description_placeholders"]["supplier"]
    created = await hass.config_entries.flow.async_configure(fid, {"next_step_id": "wizard_save"})
    await hass.async_block_till_done()
    entry = created["result"]
    assert entry.unique_id == "sommerhus" and entry.version == 3
    assert entry.data["price_unit"] == "DKK/MWh" and entry.data["vat"] == 0.25
    assert entry.data["dated_components"] == []  # EWII label did not manufacture a rate.
    assert entry.runtime_data.data["status"] != "READY"
    assert "supplier" in entry.runtime_data.data["missing_components"]
    assert "2026-10-23" in entry.runtime_data.data["reason"]
    assert "Configure" in entry.runtime_data.data["required_action"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_interrupted_options_resume_back_discard_does_not_apply(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(
        domain="nordpool", entry_id="np", data={"areas": ["DK2"]}, state=ConfigEntryState.LOADED
    )
    source.add_to_hass(hass)
    entry = await setup(hass)
    before = deepcopy(dict(entry.options))
    rows = entry.runtime_data.price_engine.records["home"]
    r = await hass.config_entries.options.async_init(entry.entry_id)
    fid = r["flow_id"]
    r = await hass.config_entries.options.async_configure(
        fid, {"name": "Changed draft name", "source_type": "nordpool"}
    )
    assert r["step_id"] == "wizard_source"
    hass.config_entries.options.async_abort(fid)
    saved = await Store(hass, 1, f"{DOMAIN}.wizard.{entry.entry_id}").async_load()
    assert saved["draft"]["name"] == "Changed draft name"
    assert dict(entry.options) == before and entry.runtime_data.price_engine.records["home"] == rows
    r = await hass.config_entries.options.async_init(entry.entry_id)
    assert r["step_id"] == "wizard_source"
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"navigation": "back"})
    assert r["step_id"] == "wizard_site"
    r = await hass.config_entries.options.async_configure(
        r["flow_id"],
        {"name": "Changed draft name", "source_type": "nordpool", "navigation": "review"},
    )
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "wizard_discard"}
    )
    assert r["step_id"] == "wizard_discard"
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"confirm": True})
    assert r["reason"] == "draft_discarded"
    assert not await Store(hass, 1, f"{DOMAIN}.wizard.{entry.entry_id}").async_load()
    assert dict(entry.options) == before
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_beta1_migration_version_display_and_immutable_api(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(domain="nordpool", entry_id="np", state=ConfigEntryState.LOADED)
    source.add_to_hass(hass)
    entry = await setup(hass)
    c = entry.runtime_data
    assert entry.version == 3
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]
    assert device.sw_version == "0.1.0-beta.3"  # Installed manifest, not flow/core version.
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    original = c.price_engine.records["home"]
    price = PriceSensor(c).native_value
    display = DisplaySensor(c, "current")
    assert display.native_value == pytest.approx(price * 100)
    assert display.native_unit_of_measurement == "øre/kWh"
    assert display.state_class is None  # Display preferences never reinterpret statistics.
    uid = display.unique_id
    r = await options_review(hass, entry.entry_id)
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "wizard_display"}
    )
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"display_unit": "DKK/kWh"})
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "wizard_save"}
    )
    await hass.async_block_till_done()
    c = entry.runtime_data
    assert c.price_engine.records["home"] == original
    assert PriceSensor(c).native_value == price
    assert DisplaySensor(c, "current").native_value == price
    assert DisplaySensor(c, "current").unique_id != uid
    assert (
        get_api(hass).lookup("home", original[0].start, original[-1].end, now=now).records
        == original
    )
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.usefixtures("price_service")
async def test_invalid_contract_fields_survive_close_and_block_silent_save(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    source = MockConfigEntry(domain="nordpool", entry_id="np", state=ConfigEntryState.LOADED)
    source.add_to_hass(hass)
    entry = await setup(hass)
    r = await options_review(hass, entry.entry_id)
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "advanced"}
    )
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "wizard_supplier"}
    )
    values = {
        "supplier": "ewii",
        "add_contract": True,
        "amount": 0.123456,
        "unit": "DKK/kWh",
        "vat_included": False,
        "rate_vat_percent": 25,
        "valid_from": "2027-01-01",
        "valid_to": "2028-01-01",
        "verified_on": "2026-10-23",
        "source": "",
    }
    r = await hass.config_entries.options.async_configure(r["flow_id"], values)
    assert r["errors"]["source"] == "rate_required"
    fid = r["flow_id"]
    hass.config_entries.options.async_abort(fid)
    r = await hass.config_entries.options.async_init(entry.entry_id)
    assert r["step_id"] == "wizard_supplier"
    schema = r["data_schema"].schema
    assert next(k.default() for k in schema if str(k) == "amount") == 0.123456
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {**values, "source": "Fictional QA contract", "navigation": "back"}
    )
    assert r["step_id"] == "wizard_grid"
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"navigation": "review"})
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "wizard_save"}
    )
    assert r["step_id"] == "wizard_supplier" and r["errors"]["base"] == "pending_page"
    assert not entry.options
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {**values, "source": "Fictional QA contract", "navigation": "review"}
    )
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"next_step_id": "wizard_save"}
    )
    assert r["type"] == "create_entry"
    await hass.async_block_till_done()
    assert len(entry.options["dated_components"]) == 3
    assert entry.options["dated_components"][-1]["amount"] == 0.123456
    assert await hass.config_entries.async_unload(entry.entry_id)
    source.mock_state(hass, ConfigEntryState.NOT_LOADED)


async def test_initial_draft_resume_and_entity_source_fields_are_separate(hass):
    r = await source_page(hass, "Sommerhus entity", "entity")
    keys = {str(k) for k in r["data_schema"].schema}
    assert "price_entity" in keys and "nordpool_entry" not in keys
    fid = r["flow_id"]
    hass.config_entries.flow.async_abort(fid)
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert r["step_id"] == "wizard_resume"
    options = next(v for k, v in r["data_schema"].schema.items() if str(k) == "draft")
    draft = next(o["value"] for o in options.config["options"] if o["value"] != "new")
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"draft": draft})
    assert r["step_id"] == "wizard_source"
    r = await hass.config_entries.flow.async_configure(
        r["flow_id"],
        {
            "price_entity": "sensor.qa_source",
            "price_unit": "DKK/kWh",
            "price_basis": "all_in",
            "price_attribute": "slots",
            "stale_minutes": 40,
        },
    )
    r = await hass.config_entries.flow.async_configure(
        r["flow_id"], {"area": "DK2", "timezone": "Europe/Copenhagen", "vat_percent": 25}
    )
    assert {str(k) for k in r["data_schema"].schema} == {
        "navigation"
    }  # No duplicate tariffs on all-in input.
    hass.config_entries.flow.async_abort(r["flow_id"])


@pytest.mark.usefixtures("price_service")
async def test_device_version_updates_without_identity_or_statistic_churn(hass, freezer):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from homeassistant.helpers import entity_registry as er

    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    device_id = devices[0].id
    canonical = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "home_current_price")
    with patch(
        "custom_components.ha_energy_price_engine.async_get_integration",
        AsyncMock(return_value=SimpleNamespace(version="0.1.0-test-update")),
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]
    assert device.id == device_id and device.sw_version == "0.1.0-test-update"
    assert (
        er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "home_current_price") == canonical
    )
    assert hass.states.get(canonical).attributes["unit_of_measurement"] == "DKK/kWh"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
@pytest.mark.parametrize(
    "released,version",
    [
        ("56cdb3c10993179371483812cbc36f651ba3ad8e", 2),
        ("0c93d2bfac88878cff46e7726f59accbeababf85", 3),
    ],
)
async def test_actual_released_beta1_sqlite_and_configuration_migrate_unchanged(
    hass, freezer, tmp_path, released, version
):
    import io
    import json
    import os
    import subprocess
    import sys
    import tarfile

    from custom_components.ha_energy_price_engine import async_migrate_entry
    from custom_components.ha_energy_price_engine.price_engine import PriceEngine

    freezer.move_to("2026-10-23T12:00:00Z")
    reference = tmp_path / "released-beta1"
    archive = await hass.async_add_executor_job(
        lambda: subprocess.check_output(
            [
                "git",
                "archive",
                released,
                "custom_components/ha_energy_price_engine",
            ]
        )
    )
    reference.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
        handle.extractall(reference, filter="data")
    config = tmp_path / "beta1-site.json"
    config.write_text(json.dumps(model()))
    expected = tmp_path / "beta1-records.json"
    script = r"""
import asyncio,json,sys
from datetime import UTC,date,datetime,timedelta
from pathlib import Path
from homeassistant.core import HomeAssistant
from custom_components.ha_energy_price_engine.configuration import tariff_for,validate_site
from custom_components.ha_energy_price_engine.price_engine import PriceEngine,day_bounds
from custom_components.ha_energy_price_engine.models import PriceSlot
import custom_components.ha_energy_price_engine as pe
assert Path(pe.__file__).resolve().is_relative_to(Path.cwd())
async def run():
 h=HomeAssistant(sys.argv[1]); e=PriceEngine(h,"released-beta1-entry"); s=validate_site(json.load(open(sys.argv[2])))
 now=datetime(2026,10,23,12,tzinfo=UTC)
 for day in (date(2026,10,23),date(2026,10,24)):
  start,end=day_bounds(day); data=[]
  while start<end:
   data.append(PriceSlot(start,start+timedelta(minutes=15),-.1));start+=timedelta(minutes=15)
  await e.async_update("home",data,tariff_for(s),{"kind":"nordpool","config_entry":"np","area":"DK2","input_unit":"DKK/MWh","input_vat":"excluded","verified_at":now.isoformat()},now)
 json.dump({"records":[e._serialize(r) for r in e.records["home"]],"revision":e.revisions["home"]},open(sys.argv[3],"w"))
 await h.async_stop()
asyncio.run(run())
"""
    await hass.async_add_executor_job(
        lambda: subprocess.run(
            [sys.executable, "-c", script, hass.config.config_dir, str(config), str(expected)],
            cwd=reference,
            env={**os.environ, "PYTHONPATH": str(reference)},
            check=True,
            capture_output=True,
            text=True,
        )
    )
    data = model()
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="released-beta1-entry",
        unique_id="home",
        version=version,
        data=data,
        options={"supplier": "ewii"},
    )
    entry.add_to_hass(hass)
    engine = PriceEngine(hass, entry.entry_id)
    before = await hass.async_add_executor_job(engine.database.path.read_bytes)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 3 and entry.unique_id == "home" and entry.data["name"] == data["name"]
    assert entry.data["nordpool_entry"] == "np" and entry.options["supplier"] == "ewii"
    assert entry.data["dated_components"] == data["dated_components"]
    assert await hass.async_add_executor_job(engine.database.path.read_bytes) == before
    await engine.async_load(["home"])
    old = json.loads(expected.read_text())
    assert [engine._serialize(r) for r in engine.records["home"]] == old["records"]
    assert engine.revisions["home"] == old["revision"] and not engine.load_errors


@pytest.mark.usefixtures("price_service")
async def test_save_verify_unchanged_options_rechecks_sources_and_preserves_history(hass, freezer):
    from unittest.mock import patch

    from custom_components.ha_energy_price_engine.configuration import settings

    freezer.move_to("2026-10-23T12:00:00Z")
    MockConfigEntry(
        domain="nordpool", entry_id="np", data={"areas": ["DK2"]}, state=ConfigEntryState.LOADED
    ).add_to_hass(hass)
    entry = await setup(hass)
    rows = entry.runtime_data.price_engine.records["home"]
    revision = entry.runtime_data.price_engine.revisions["home"]
    # Persist a complete options model once, then Save an identical draft.
    hass.config_entries.async_update_entry(entry, options=settings(entry))
    await hass.async_block_till_done()
    result = await options_review(hass, entry.entry_id)
    with patch.object(
        hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
    ) as reload:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "wizard_save"}
        )
        await hass.async_block_till_done()
        reload.assert_awaited_once_with(entry.entry_id)
    assert result["type"] == "create_entry"
    assert entry.runtime_data.price_engine.records["home"] == rows
    assert entry.runtime_data.price_engine.revisions["home"] == revision
    assert await hass.config_entries.async_unload(entry.entry_id)
