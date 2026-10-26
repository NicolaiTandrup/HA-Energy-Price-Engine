"""Pinned real HACS prerelease discovery and source-tag installation.

PE_PUBLIC_RELEASE_RECEIPT supplies independently downloaded public metadata/bytes;
without it the same workflow runs with deterministic prepublication fixtures.
"""

import base64
import importlib
import io
import json
import os
import zipfile
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiogithubapi.models.release import GitHubReleaseModel
from awesomeversion import AwesomeVersion

from tools.prepare_hacs_reference import PINS

from .test_hacs_workflow import candidate_tree, upstream

ROOT = Path(__file__).parents[1]
TAG = "v0.1.0-beta.1"
DOMAIN = "ha_energy_price_engine"


def release_inputs():
    if path := os.environ.get("PE_PUBLIC_RELEASE_RECEIPT"):
        receipt = json.loads(Path(path).read_text())
        with zipfile.ZipFile(receipt["source_archive"]) as archive:
            files = {
                "/".join(p.split("/")[1:]): archive.read(p)
                for p in archive.namelist()
                if not p.endswith("/")
            }
        return receipt, files, Path(receipt["source_archive"]).read_bytes()
    files = candidate_tree()
    files["README.md"] = b"Energy Price Engine read-only beta\n"
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as handle:
        for path, content in files.items():
            handle.writestr("release-source/" + path, content)
    return (
        {
            "repository": {
                "full_name": "NicolaiTandrup/HA-Energy-Price-Engine",
                "id": 12345,
                "default_branch": "main",
                "archived": False,
            },
            "source_commit": "synthetic-validated-source",
            "release": {"tag_name": TAG, "draft": False, "prerelease": True, "assets": []},
        },
        files,
        archive.getvalue(),
    )


@pytest.mark.parametrize("line", list(PINS))
async def test_hacs_add_discover_beta_download_update_and_reinstall(hass, tmp_path, line):
    receipt, files, archive = release_inputs()
    assert receipt["release"]["prerelease"] and not receipt["release"]["draft"]
    assert receipt["release"]["tag_name"] == TAG
    alias = upstream(line)
    base = importlib.import_module(alias + ".base")
    repo_base = importlib.import_module(alias + ".repositories.base")
    enums = importlib.import_module(alias + ".enums")
    hacs = base.HacsBase()
    hacs.hass = hass
    hacs.core.config_path = tmp_path
    hacs.core.ha_version = AwesomeVersion(version("homeassistant"))
    hacs.version = AwesomeVersion("2.0.5")
    hacs.queue = SimpleNamespace(has_pending_tasks=False)
    hacs.async_dispatch = Mock()
    hacs.githubapi = SimpleNamespace(repos=SimpleNamespace(contents=SimpleNamespace(get=Mock())))
    repository = receipt["repository"]["full_name"]
    obj = SimpleNamespace(
        full_name=repository,
        attributes=receipt["repository"],
        last_commit=receipt["source_commit"],
        set_last_commit=AsyncMock(),
    )
    directories = {str(p) for name in files for p in Path(name).parents if str(p) != "."}
    tree = [
        SimpleNamespace(
            path=p,
            full_path=p,
            filename=Path(p).name,
            is_directory=p in directories,
            type="tree" if p in directories else "blob",
            url="https://api.github.com/recorded-public-tree",
        )
        for p in sorted(set(files) | directories)
    ]
    calls = []

    async def contents(*, path, **kwargs):
        return SimpleNamespace(data=SimpleNamespace(content=base64.b64encode(files[path]).decode()))

    async def download(url, **kwargs):
        calls.append(url)
        if url.endswith(f"/archive/refs/tags/{TAG}.zip"):
            return archive
        if "raw.githubusercontent.com" in url:
            name = url.split(f"/{TAG}/", 1)[-1]
            return files.get(name, b"Read-only beta")
        raise AssertionError(f"Unexpected HACS download: {url}")

    async def last_commits(repo):
        repo.data.last_commit = receipt["source_commit"]

    hacs.async_github_api_method = AsyncMock(side_effect=contents)
    hacs.async_download_file = AsyncMock(side_effect=download)
    real_backup = repo_base.Backup

    def isolated_backup(**kwargs):
        kwargs.setdefault("backup_path", str(tmp_path / "hacs-backup") + "/")
        return real_backup(**kwargs)

    hass.data["custom_components"] = {}
    with (
        patch.object(
            repo_base.HacsRepository,
            "async_get_legacy_repository_object",
            AsyncMock(return_value=(obj, "recorded-public-response")),
        ),
        patch.object(
            repo_base.HacsRepository,
            "get_releases",
            AsyncMock(return_value=[GitHubReleaseModel(receipt["release"])]),
        ),
        patch.object(repo_base.HacsRepository, "get_tree", AsyncMock(return_value=tree)),
        patch.object(repo_base.HacsRepository, "async_set_last_commits", last_commits, create=True),
        patch.object(repo_base, "Backup", side_effect=isolated_backup),
    ):
        # The ordinary custom-repository add succeeds even before beta versions are shown.
        await hacs.async_register_repository(repository, enums.HacsCategory.INTEGRATION)
        repo = hacs.repositories.get_by_full_name(repository)
        assert repo and repo.data.domain == DOMAIN and repo.data.config_flow
        assert repo.data.manifest_name == "Energy Price Engine"
        assert repo.data.prerelease == TAG and TAG not in repo.data.published_tags
        repo.data.show_beta = True  # Same state set by HACS's Show beta versions action.
        await repo.update_repository(force=True)
        assert TAG in repo.data.published_tags
        repo.data.selected_tag = TAG
        assert repo.version_to_download() == TAG
        installed = tmp_path / "custom_components" / DOMAIN
        for _ in range(2):
            await repo.async_download_repository(ref=TAG)
            assert repo.data.installed and repo.data.installed_version == TAG
            expected = {
                str(Path(p).relative_to(f"custom_components/{DOMAIN}")): body
                for p, body in files.items()
                if p.startswith(f"custom_components/{DOMAIN}/")
            }
            assert {
                str(p.relative_to(installed)): p.read_bytes()
                for p in installed.rglob("*")
                if p.is_file()
            } == expected
            assert json.loads((installed / "manifest.json").read_text())[
                "version"
            ] == TAG.removeprefix("v")
        await repo.uninstall()
        assert not installed.exists()
        await repo.async_download_repository(ref=TAG)
        assert (installed / "config_flow.py").is_file()
        assert calls.count(f"https://github.com/{repository}/archive/refs/tags/{TAG}.zip") == 3
