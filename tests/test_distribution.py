"""Distribution bytes are reproducible, licensed and contain runtime files only."""

import json
import zipfile
from pathlib import Path

from tools.build_beta import build


def test_reproducible_safe_hacs_and_manual_archives(tmp_path):
    first = build(tmp_path / "one", allow_dirty=True)
    second = build(tmp_path / "two", allow_dirty=True)
    assert first["archives"] == second["archives"]
    assert first["version"] == "0.1.0-beta.5" and first["published"] is False
    for name in first["archives"]:
        with zipfile.ZipFile(tmp_path / "one" / name) as archive:
            prefix = "custom_components/ha_energy_price_engine/" if "-manual" in name else ""
            names = archive.namelist()
            assert prefix + "LICENSE" in names and prefix + "ledger.py" in names
            assert json.loads(archive.read(prefix + "manifest.json"))["version"] == "0.1.0-beta.5"
            assert not any(
                "__pycache__" in p
                or "consumer-references" in p
                or ".sqlite" in p
                or ".." in Path(p).parts
                for p in names
            )
            for file in names:
                if file.endswith(".py"):
                    compile(archive.read(file), file, "exec")
