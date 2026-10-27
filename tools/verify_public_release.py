"""Independently download/verify the public PE prerelease and run real isolated HACS.

Read-only network access; no publishing, repository settings or live HA access.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "NicolaiTandrup/HA-Energy-Price-Engine"
TAG = "v0.1.0-beta.2"
DOMAIN = "ha_energy_price_engine"


def api(endpoint):
    return json.loads(subprocess.check_output(["gh", "api", endpoint], text=True))


def download(url, destination, asset_id=None):
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "PE-release-integrity-check"}),
            timeout=60,
        ) as response:
            destination.write_bytes(response.read())
    except OSError:
        if asset_id is None:
            raise
        with destination.open("wb") as output:
            subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{REPOSITORY}/releases/assets/{asset_id}",
                    "-H",
                    "Accept: application/octet-stream",
                ],
                stdout=output,
                check=True,
            )


def verify(output, expected_commit):
    output.mkdir(parents=True, exist_ok=True)
    release = api(f"repos/{REPOSITORY}/releases/tags/{TAG}")
    assert release["prerelease"] is True and release["draft"] is False
    assert release["tag_name"] == TAG
    source_commit = api(f"repos/{REPOSITORY}/commits/{TAG}")["sha"]
    assert source_commit == expected_commit, "Public tag differs from validated source"
    repository = api(f"repos/{REPOSITORY}")
    assert repository["default_branch"] == "main"
    main_commit = api(f"repos/{REPOSITORY}/commits/main")["sha"]
    main_tree = api(f"repos/{REPOSITORY}/git/trees/main?recursive=1")
    assert f"custom_components/{DOMAIN}/manifest.json" in {p["path"] for p in main_tree["tree"]}
    asset_map = {a["name"]: a for a in release["assets"]}
    required = {f"{DOMAIN}.zip", f"{DOMAIN}-manual.zip", "BUILD_MANIFEST.json", "SHA256SUMS"}
    assert required <= asset_map.keys(), "Published release assets incomplete"
    for name in required:
        asset = asset_map[name]
        download(asset["browser_download_url"], output / name, asset["id"])
        if asset.get("digest"):
            assert (
                asset["digest"]
                == "sha256:" + hashlib.sha256((output / name).read_bytes()).hexdigest()
            )
    manifest = json.loads((output / "BUILD_MANIFEST.json").read_text())
    assert manifest["commit"] == expected_commit and manifest["dirty"] is False
    assert manifest["version"] == TAG.removeprefix("v")
    sums = {}
    for line in (output / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split()
        sums[name] = digest
    assert sums == manifest["archives"]
    for name, digest in sums.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    source = output / "public-tag-source.zip"
    source_url = f"https://codeload.github.com/{REPOSITORY}/zip/refs/tags/{TAG}"
    download(source_url, source)
    with zipfile.ZipFile(source) as archive:
        roots = {p.split("/")[0] for p in archive.namelist()}
        assert len(roots) == 1
        prefix = next(iter(roots)) + "/"
        for name, digest in manifest["runtime_files"].items():
            path = "LICENSE" if name == "LICENSE" else f"custom_components/{DOMAIN}/{name}"
            assert hashlib.sha256(archive.read(prefix + path)).hexdigest() == digest
    for name in sums:
        with zipfile.ZipFile(output / name) as archive:
            prefix = f"custom_components/{DOMAIN}/" if "-manual" in name else ""
            actual = {
                p.removeprefix(prefix): hashlib.sha256(archive.read(p)).hexdigest()
                for p in archive.namelist()
            }
            assert actual == manifest["runtime_files"], "Published ZIP differs from source payload"
    main_source = output / "public-main-source.zip"
    download(f"https://codeload.github.com/{REPOSITORY}/zip/{main_commit}", main_source)
    receipt = {
        "main_archive": str(main_source.resolve()),
        "verified_at": datetime.now(UTC).isoformat(),
        "repository": repository,
        "release": release,
        "main_commit": main_commit,
        "source_commit": source_commit,
        "source_archive": str(source.resolve()),
        "source_archive_url": source_url,
        "archive_hashes": sums,
    }
    path = output / "PUBLIC_RELEASE_RECEIPT.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    environment = {**os.environ, "PE_PUBLIC_RELEASE_RECEIPT": str(path.resolve())}
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_hacs_release.py",
            "-q",
            "-W",
            "error::ResourceWarning",
        ],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    for name in sums:
        subprocess.run(
            [sys.executable, str(ROOT / "tools/smoke_install_package.py"), str(output / name)],
            check=True,
        )
    receipt["isolated_hacs_and_native_install"] = "passed"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                "release": release["html_url"],
                "source_commit": source_commit,
                "assets_verified": sorted(required),
                "isolated_hacs": "passed",
                "receipt": str(path),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify(args.output, args.expected_commit)
