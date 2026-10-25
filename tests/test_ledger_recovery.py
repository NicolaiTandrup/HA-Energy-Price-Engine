"""Real disk transactions, interrupted writers, checksums and offline recovery."""

import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from custom_components.ha_energy_price_engine.ledger import (
    inspect_ledger,
    restore_ledger,
)
from custom_components.ha_energy_price_engine.price_engine import PriceEngine

from .test_price_engine import rows

NOW = datetime(2026, 10, 23, tzinfo=UTC)


async def seed(hass, entry="disk"):
    engine = PriceEngine(hass, entry)
    await engine.async_update("home", rows(), {"mode": "all_in"}, {"provider": "synthetic"}, NOW)
    return engine


async def test_legacy_migration_is_verified_idempotent_and_preserves_original(hass):
    first = await seed(hass, "original")
    records = [first._serialize(r) for r in first.records["home"]]
    target = PriceEngine(hass, "migration")
    legacy = {"records": records, "revision": 1, "signature": "legacy", "batch_signatures": {}}
    await target.store("home").async_save(legacy)
    await target.async_load(["home"])
    assert len(target.records["home"]) == 96
    assert await target.store("home").async_load() == legacy
    await target.async_load(["home"])
    report = await hass.async_add_executor_job(inspect_ledger, target.database.path)
    assert report["sites"]["home"] == {"records": 96, "revision": 1}


async def test_interrupted_sqlite_transaction_rolls_back_on_actual_reopen(hass):
    engine = await seed(hass)
    original = engine.records["home"]
    code = """import sqlite3,sys,os
c=sqlite3.connect(sys.argv[1]);c.execute('BEGIN IMMEDIATE')
c.execute('UPDATE prices SET amount=999 WHERE site=?',('home',))
os._exit(0)
"""
    await hass.async_add_executor_job(
        subprocess.run, [sys.executable, "-c", code, str(engine.database.path)]
    )
    restored = PriceEngine(hass, "disk")
    await restored.async_load(["home"])
    assert restored.records["home"] == original
    assert not restored.load_errors


async def test_stale_writer_cannot_overwrite_later_configuration(hass):
    first = await seed(hass)
    stale = PriceEngine(hass, "disk")
    await stale.async_load(["home"])
    await first.async_update(
        "home", rows(), {"mode": "spot_ex_vat", "vat": 0.25}, {"revision": "new"}, NOW
    )
    with pytest.raises(OSError, match="Stale ledger writer"):
        await stale.async_update(
            "home", rows(), {"mode": "spot_ex_vat", "vat": 0.5}, {"revision": "stale"}, NOW
        )
    restored = PriceEngine(hass, "disk")
    await restored.async_load(["home"])
    assert restored.records["home"] == first.records["home"]


@pytest.mark.parametrize("corruption", ["bytes", "amount", "provenance"])
async def test_corrupt_history_is_preserved_and_cannot_be_overwritten(hass, corruption):
    engine = await seed(hass)
    path = engine.database.path

    def corrupt():
        if corruption == "bytes":
            path.write_bytes(b"corrupted-authoritative-history")
        else:
            with closing(sqlite3.connect(path, isolation_level=None)) as c:
                if corruption == "amount":
                    c.execute("UPDATE prices SET amount=987")
                else:
                    c.execute("UPDATE blobs SET body=?", (b"corrupt",))
        return path.read_bytes()

    before = await hass.async_add_executor_job(corrupt)
    restored = PriceEngine(hass, "disk")
    await restored.async_load(["home"])
    assert restored.load_errors["home"] and not restored.records["home"]
    with pytest.raises(OSError, match="requires recovery"):
        await restored.async_update("home", rows(), {"mode": "all_in"}, {}, NOW)
    assert await hass.async_add_executor_job(path.read_bytes) == before


async def test_verified_backup_and_explicit_offline_restore_preserve_corrupt_original(
    hass, tmp_path
):
    engine = await seed(hass)
    original = engine.records["home"]
    backup = tmp_path / "verified.sqlite3"
    await engine.database.async_backup(backup)
    with pytest.raises(FileExistsError):
        await engine.database.async_backup(backup)
    await hass.async_add_executor_job(engine.database.path.write_bytes, b"corrupt")
    with pytest.raises(ValueError, match="Stop Home Assistant"):
        restore_ledger(backup, engine.database.path)
    report = await hass.async_add_executor_job(
        lambda: restore_ledger(backup, engine.database.path, confirm_offline=True)
    )
    assert Path(report["preserved_original"]).read_bytes() == b"corrupt"
    restored = PriceEngine(hass, "disk")
    await restored.async_load(["home"])
    assert restored.records["home"] == original


async def test_actual_sql_error_rolls_back_revision_audit_and_amounts(hass):
    engine = await seed(hass)
    original = engine.records["home"]
    original_blob = engine.database._blob
    count = 0

    def fail_halfway(connection, value):
        nonlocal count
        count += 1
        if count == 7:
            raise sqlite3.OperationalError("simulated I/O failure")
        return original_blob(connection, value)

    with patch.object(engine.database, "_blob", side_effect=fail_halfway):
        with pytest.raises(OSError, match="transaction failed"):
            await engine.async_update("home", rows(), {"mode": "spot_ex_vat", "vat": 0.25}, {}, NOW)
    assert engine.records["home"] == original
    restored = PriceEngine(hass, "disk")
    await restored.async_load(["home"])
    assert restored.records["home"] == original and restored.revisions["home"] == 1
    assert restored.audit["home"] == []


async def test_local_backup_cli_exercises_real_verified_files(hass, tmp_path):
    import json

    engine = await seed(hass)
    script = Path(__file__).resolve().parents[1] / "tools/ledger_backup.py"
    inspected = await hass.async_add_executor_job(
        lambda: subprocess.run(
            [sys.executable, str(script), "inspect", str(engine.database.path)],
            capture_output=True,
            text=True,
            check=True,
        )
    )
    assert json.loads(inspected.stdout)["sites"]["home"]["records"] == 96
    target = tmp_path / "cli-backup.sqlite3"
    copied = await hass.async_add_executor_job(
        lambda: subprocess.run(
            [sys.executable, str(script), "backup", str(engine.database.path), str(target)],
            capture_output=True,
            text=True,
            check=True,
        )
    )
    assert json.loads(copied.stdout)["backup"] == str(target)
    denied = await hass.async_add_executor_job(
        lambda: subprocess.run(
            [sys.executable, str(script), "restore", str(target), str(engine.database.path)],
            capture_output=True,
            text=True,
        )
    )
    assert denied.returncode == 1 and "Stop Home Assistant" in denied.stderr


async def test_year_scale_append_preserves_database_enforced_historical_freeze(hass):
    from datetime import timedelta

    from custom_components.ha_energy_price_engine.models import PriceSlot

    engine = PriceEngine(hass, "year-scale")
    start = datetime(2025, 1, 1, tzinfo=UTC)
    data = [
        PriceSlot(start + timedelta(minutes=15 * i), start + timedelta(minutes=15 * (i + 1)), -0.1)
        for i in range(365 * 96)
    ]
    await engine.async_update(
        "home", data, {"mode": "all_in"}, {"provider": "synthetic-year-scale"}, NOW
    )

    def freeze():
        with closing(sqlite3.connect(engine.database.path, isolation_level=None)) as c:
            c.execute(
                "CREATE TRIGGER freeze_published_history BEFORE INSERT ON prices WHEN NEW.start < '2026-01-01' BEGIN SELECT RAISE(ABORT,'attempted historical rewrite'); END"
            )

    await hass.async_add_executor_job(freeze)
    await engine.async_update(
        "home", rows(), {"mode": "all_in"}, {"provider": "new-synthetic-publication"}, NOW
    )
    restored = PriceEngine(hass, "year-scale")
    await restored.async_load(["home"])
    assert len(restored.records["home"]) == 365 * 96 + 96
    assert restored.records["home"][0].start == start
    assert restored.records["home"][0].final_price_incl_vat == -0.1
    assert not restored.load_errors
    with patch(
        "custom_components.ha_energy_price_engine.price_engine.calculate",
        side_effect=AssertionError("historical read arithmetic"),
    ):
        assert len(restored.lookup("home", start, start + timedelta(days=1))) == 96
