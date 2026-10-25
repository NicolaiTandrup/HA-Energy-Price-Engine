"""Extract an archive outside the checkout and load it in a fresh real HA harness."""

import argparse
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

TEST = r"""
import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import pytest
from homeassistant.config_entries import ConfigEntryState
from custom_components import ha_energy_price_engine as integration
from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.price_engine import day_bounds

@pytest.fixture
def hass_config_dir():
    return os.environ["PE_PACKAGE_ROOT"]

async def test_independent_installed_package(hass, freezer, enable_custom_integrations):
    root=Path(os.environ["PE_PACKAGE_ROOT"])
    assert Path(integration.__file__).resolve().is_relative_to(root)
    manifest=json.loads((Path(integration.__file__).parent/"manifest.json").read_text())
    assert manifest["version"]=="0.1.0-beta.1"
    freezer.move_to("2026-10-24T10:00:00Z")
    now=datetime(2026,10,24,10,tzinfo=UTC)
    slots=[]
    for day in (date(2026,10,24),date(2026,10,25)):
        start,end=day_bounds(day)
        while start<end:
            slots.append({"start":start.isoformat(),"end":(start+timedelta(minutes=15)).isoformat(),"price":-.25})
            start+=timedelta(minutes=15)
    hass.states.async_set("sensor.package_source","-.25",{"slots":slots,"currency":"DKK","unit_of_measurement":"DKK/kWh","vat_included":True,"verified_at":now.isoformat()})
    form=await hass.config_entries.flow.async_init("ha_energy_price_engine",context={"source":"user"})
    assert form["type"]=="form"
    created=await hass.config_entries.flow.async_configure(form["flow_id"],{
        "id":"installed","name":"Installed package","source_type":"entity","price_entity":"sensor.package_source",
        "price_unit":"DKK/kWh","price_basis":"all_in","price_attribute":"slots","stale_minutes":40,
        "area":"DK2","timezone":"Europe/Copenhagen","vat":.25})
    assert created["type"]=="create_entry"
    await hass.async_block_till_done()
    entry=created["result"]
    assert entry.state==ConfigEntryState.LOADED
    result=get_api(hass).lookup("installed",*day_bounds(date(2026,10,25)),now=now)
    assert str(result.status)=="READY" and len(result.records)==100
    assert all(r.final_price_incl_vat==-.25 for r in result.records)
    before=result.records
    assert entry.runtime_data.price_engine.database.path.is_file()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert get_api(hass).lookup("installed",*day_bounds(date(2026,10,25)),now=now).records==before
    options=await hass.config_entries.options.async_init(entry.entry_id)
    assert options["type"]=="menu"
    hass.config_entries.options.async_abort(options["flow_id"])
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
"""


def smoke(archive):
    archive = Path(archive).resolve()
    with tempfile.TemporaryDirectory(prefix="pe-independent-install-") as directory:
        root = Path(directory)
        with zipfile.ZipFile(archive) as candidate:
            names = candidate.namelist()
            manual = "custom_components/ha_energy_price_engine/manifest.json" in names
            destination = root if manual else root / "custom_components/ha_energy_price_engine"
            for name in names:
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("Unsafe archive path")
            candidate.extractall(destination)
        test = root / "test_package_install.py"
        test.write_text(TEST)
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(root)
        environment["PE_PACKAGE_ROOT"] = str(root)
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "pytest_homeassistant_custom_component",
                "-o",
                "asyncio_mode=auto",
                "-o",
                "asyncio_default_fixture_loop_scope=function",
                "-q",
                str(test),
            ],
            cwd=root,
            env=environment,
        )
        if completed.returncode:
            raise SystemExit(completed.returncode)
        print(
            "Verified independent install:",
            archive.name,
            "(manual layout)" if manual else "(HACS asset layout)",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    smoke(parser.parse_args().archive)
