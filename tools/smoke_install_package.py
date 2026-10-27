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

@pytest.fixture(autouse=True)
def release_metadata():
    from unittest.mock import AsyncMock,patch
    with (patch("custom_components.ha_energy_price_engine.update.fetch_releases",AsyncMock(return_value=[])),patch("custom_components.ha_energy_price_engine.supplier_offers._fetch",AsyncMock(side_effect=OSError("Offline source")))):
        yield

@pytest.fixture
def hass_config_dir():
    return os.environ["PE_PACKAGE_ROOT"]

async def test_independent_installed_package(hass, freezer, enable_custom_integrations):
    root=Path(os.environ["PE_PACKAGE_ROOT"])
    assert Path(integration.__file__).resolve().is_relative_to(root)
    manifest=json.loads((Path(integration.__file__).parent/"manifest.json").read_text())
    assert manifest["version"]=="0.1.0-beta.6"
    freezer.move_to("2026-10-24T10:00:00Z")
    now=datetime(2026,10,24,10,tzinfo=UTC)
    from homeassistant.core import SupportsResponse
    from pytest_homeassistant_custom_component.common import MockConfigEntry,MockModule,mock_integration
    mock_integration(hass,MockModule("nordpool"))
    source=MockConfigEntry(domain="nordpool",entry_id="package-np",data={"areas":["DK2"]},state=ConfigEntryState.LOADED)
    source.add_to_hass(hass)
    async def prices(call):
        start,end=day_bounds(date.fromisoformat(call.data["date"]));rows=[]
        while start<end:
            rows.append({"start":start.isoformat(),"end":(start+timedelta(minutes=15)).isoformat(),"price":-250});start+=timedelta(minutes=15)
        return {"DK2":rows}
    hass.services.async_register("nordpool","get_prices_for_date",prices,supports_response=SupportsResponse.ONLY)
    form=await hass.config_entries.flow.async_init("ha_energy_price_engine",context={"source":"user"})
    assert form["type"]=="form"
    async def complete_wizard(form):
        flow=form["flow_id"]
        for page in [
            {"name":"Installed","nordpool_entry":source.entry_id},
            {"grid":"manual"},
            {"amount":20,"vat_included":False,"confirm":True},
            {"amount":"11.1","vat_included":False},
        ]:
            form=await hass.config_entries.flow.async_configure(flow,page)
            assert form["type"] in ("form","menu"),form
        assert form["step_id"]=="setup_review"
        entry=next(e for e in hass.config_entries.async_entries("ha_energy_price_engine") if e.unique_id=="installed")
        hass.config_entries.flow.async_abort(flow)
        return entry
    entry=await complete_wizard(form)
    await hass.async_block_till_done()
    assert entry.state==ConfigEntryState.LOADED
    result=get_api(hass).lookup("installed",*day_bounds(date(2026,10,25)),now=now)
    assert str(result.status)=="READY" and len(result.records)==100
    assert all(abs(r.final_price_incl_vat-.23)<1e-9 for r in result.records)
    before=result.records
    assert entry.runtime_data.price_engine.database.path.is_file()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert get_api(hass).lookup("installed",*day_bounds(date(2026,10,25)),now=now).records==before
    options=await hass.config_entries.options.async_init(entry.entry_id)
    assert options["type"]=="menu" and options["step_id"]=="setup_review"
    hass.config_entries.options.async_abort(options["flow_id"])
    old_id=entry.entry_id
    old_ledger=entry.runtime_data.price_engine.database.path
    result=await hass.config_entries.async_remove(old_id)
    assert result["require_restart"] is False
    assert old_ledger.is_file()  # Removal cannot erase accounting references.
    form=await hass.config_entries.flow.async_init("ha_energy_price_engine",context={"source":"user"})
    replacement=await complete_wizard(form)
    await hass.async_block_till_done()
    assert replacement.entry_id != old_id and replacement.state==ConfigEntryState.LOADED
    assert replacement.runtime_data.price_engine.database.path != old_ledger
    assert get_api(hass).lookup("installed",*day_bounds(date(2026,10,25)),now=now).records
    assert await hass.config_entries.async_unload(replacement.entry_id)
    source.mock_state(hass,ConfigEntryState.NOT_LOADED)
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
