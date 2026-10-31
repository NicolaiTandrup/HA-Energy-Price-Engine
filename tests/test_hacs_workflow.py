"""Actual pinned HACS add/install code; mocked GitHub I/O, never owner's HA/settings."""

import base64
import importlib
import io
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tools.prepare_hacs_reference import PINS

ROOT = Path(__file__).parents[1]
RECEIPTS = json.loads((ROOT / "docs/contracts/hacs-default-branches.json").read_text())


def upstream(line):
    root = ROOT / "hacs-references" / line
    assert (root / "SOURCE_COMMIT").read_text().strip() == PINS[line], (
        "Prepare pinned HACS references"
    )
    alias = "pe_hacs_" + line
    if alias not in sys.modules:
        package = ModuleType(alias)
        package.__path__ = [str(root / "custom_components/hacs")]
        sys.modules[alias] = package
    return alias


def candidate_tree(reference="pe"):
    root = ROOT if reference == "pe" else ROOT / "consumer-references" / reference
    domain = "ha_energy_price_engine" if reference == "pe" else "ev_charge_manager"
    base = root / "custom_components" / domain
    files = {
        str(p.relative_to(root)): p.read_bytes()
        for p in base.rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".json", ".png", ".js"}
        and "__pycache__" not in p.parts
    }
    files["hacs.json"] = (root / "hacs.json").read_bytes()
    return files


@pytest.mark.parametrize("line", list(PINS))
@pytest.mark.parametrize("repository", list(RECEIPTS))
async def test_recorded_prebootstrap_branch_reproduces_hacs_rejection(
    hass, tmp_path, line, repository
):
    alias = upstream(line)
    base = importlib.import_module(alias + ".base")
    repository_base = importlib.import_module(alias + ".repositories.base")
    enums = importlib.import_module(alias + ".enums")
    errors = importlib.import_module(alias + ".exceptions")
    hacs = base.HacsBase()
    hacs.hass = hass
    hacs.queue = SimpleNamespace(has_pending_tasks=False)
    hacs.core.config_path = tmp_path
    hacs.async_dispatch = Mock()
    snapshot = RECEIPTS[repository]
    assert snapshot["default_branch"] == "main"
    assert snapshot["paths"] == ["LICENSE", "README.md"]
    obj = SimpleNamespace(
        full_name=repository,
        set_last_commit=AsyncMock(),
        last_commit="synthetic-approved-head",
        attributes={
            "full_name": repository,
            "id": "12345",
            "default_branch": "main",
            "archived": False,
        },
    )
    tree = [
        SimpleNamespace(
            path=p,
            full_path=p,
            filename=Path(p).name,
            is_directory=False,
            type="blob",
            url="https://api.github.com/synthetic",
        )
        for p in snapshot["paths"]
    ]
    with (
        patch.object(
            repository_base.HacsRepository,
            "async_get_legacy_repository_object",
            AsyncMock(return_value=(obj, "recorded")),
        ),
        patch.object(repository_base.HacsRepository, "get_releases", AsyncMock(return_value=[])),
        patch.object(repository_base.HacsRepository, "get_tree", AsyncMock(return_value=tree)),
    ):
        with pytest.raises(
            errors.HacsException, match="Repository structure for main is not compliant"
        ):
            await hacs.async_register_repository(repository, enums.HacsCategory.INTEGRATION)
    assert not hacs.repositories.get_by_full_name(repository)


@pytest.mark.parametrize("line", list(PINS))
@pytest.mark.parametrize("reference", ["pe"])
async def test_candidate_after_approved_default_branch_gate_installs_via_actual_hacs(
    hass, tmp_path, line, reference
):
    alias = upstream(line)
    base = importlib.import_module(alias + ".base")
    repository_base = importlib.import_module(alias + ".repositories.base")
    enums = importlib.import_module(alias + ".enums")
    hacs = base.HacsBase()
    hacs.hass = hass
    hacs.queue = SimpleNamespace(has_pending_tasks=False)
    hacs.core.config_path = tmp_path
    hacs.async_dispatch = Mock()
    domain = "ha_energy_price_engine" if reference == "pe" else "ev_charge_manager"
    repository = "nicolaitandrup/" + (
        "ha-energy-price-engine" if reference == "pe" else "ha-ev-charge-manager"
    )
    files = candidate_tree(reference)
    directories = {
        str(parent) for path in files for parent in Path(path).parents if str(parent) != "."
    }
    tree = [
        SimpleNamespace(
            path=p,
            full_path=p,
            filename=Path(p).name,
            is_directory=p in directories,
            type="tree" if p in directories else "blob",
            url="https://api.github.com/synthetic",
        )
        for p in sorted(set(files) | directories)
    ]
    obj = SimpleNamespace(
        full_name=repository,
        set_last_commit=AsyncMock(),
        last_commit="synthetic-approved-head",
        attributes={
            "full_name": repository,
            "id": "12345",
            "default_branch": "main",
            "archived": False,
        },
    )

    async def contents(*, path, **kwargs):
        return SimpleNamespace(data=SimpleNamespace(content=base64.b64encode(files[path]).decode()))

    hacs.githubapi = SimpleNamespace(repos=SimpleNamespace(contents=SimpleNamespace(get=Mock())))
    hacs.async_github_api_method = AsyncMock(side_effect=contents)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        for path, payload in files.items():
            z.writestr("candidate-main/" + path, payload)
    requests = []

    async def download(url, **kwargs):
        requests.append(url)
        if "/archive/refs/tags/main.zip" in url:
            return None  # No main tag exists: actual HACS must fall back to the branch.
        assert "/archive/refs/heads/main.zip" in url
        return archive.getvalue()

    hacs.async_download_file = AsyncMock(side_effect=download)
    hass.data["custom_components"] = {}

    async def commit_lookup(repo):
        repo.data.last_commit = "synthetic-approved-head"

    real_backup = repository_base.Backup

    def isolated_backup(**kwargs):
        kwargs.setdefault("backup_path", str(tmp_path / "hacs-backups") + "/")
        return real_backup(**kwargs)

    with (
        patch.object(repository_base, "Backup", side_effect=isolated_backup),
        patch.object(
            repository_base.HacsRepository,
            "async_get_legacy_repository_object",
            AsyncMock(return_value=(obj, "candidate")),
        ),
        patch.object(repository_base.HacsRepository, "get_releases", AsyncMock(return_value=[])),
        patch.object(repository_base.HacsRepository, "get_tree", AsyncMock(return_value=tree)),
        patch.object(
            repository_base.HacsRepository, "async_set_last_commits", commit_lookup, create=True
        ),
    ):
        await hacs.async_register_repository(repository, enums.HacsCategory.INTEGRATION)
        repo = hacs.repositories.get_by_full_name(repository)
        assert repo and repo.data.domain == domain
        assert repo.content.path.remote == f"custom_components/{domain}"
        await repo.async_install()
        assert repo.data.installed
        assert repo.data.installed_commit == "synthetic-approved-head"
        installed = tmp_path / "custom_components" / domain
        assert json.loads((installed / "manifest.json").read_text())["config_flow"] is True
        assert (installed / "config_flow.py").is_file()
        assert (installed / "translations/en.json").is_file()
        assert all(
            (installed / Path(path).relative_to(f"custom_components/{domain}")).read_bytes()
            == payload
            for path, payload in files.items()
            if path.startswith(f"custom_components/{domain}/")
        )
        assert requests[:2] == [
            f"https://github.com/{repository}/archive/refs/tags/main.zip",
            f"https://github.com/{repository}/archive/refs/heads/main.zip",
        ]
        # Actual HACS update exercises its backup/replace/restore path too.
        await repo.async_install()
        assert (installed / "config_flow.py").is_file()
        await repo.uninstall()
        assert not installed.exists()
        assert not repo.data.installed
        await repo.async_install()
        assert (installed / "manifest.json").is_file()


@pytest.mark.parametrize("line", list(PINS))
def test_branch_url_does_not_bypass_default_branch_registration(line):
    regex = importlib.import_module(upstream(line) + ".utils.regex")
    assert (
        regex.extract_repository_from_url(
            "https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/tree/feat/standalone-price-engine"
        )
        == "nicolaitandrup/ha-energy-price-engine"
    )
