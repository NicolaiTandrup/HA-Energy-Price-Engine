"""Build reproducible HACS-root and HA-config-root candidate archives; never publish."""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "ha_energy_price_engine"
PACKAGE = PurePosixPath("custom_components") / DOMAIN
REQUIRED = {
    "manifest.json",
    "presentation.py",
    "device_diagnostics.py",
    "dashboard.py",
    "www/energy-price-engine-card.js",
    "data/decimal_symbols.json",
    "__init__.py",
    "api.py",
    "config_flow.py",
    "sensor.py",
    "ledger.py",
    "repairs.py",
    "strings.json",
    "translations/en.json",
    "brand/icon.png",
}


def build(output, *, allow_dirty=False):
    dirty = bool(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"], text=True
        ).strip()
    )
    if dirty and not allow_dirty:
        raise ValueError(
            "Commit tracked changes first, or explicitly use --allow-dirty for development smoke testing"
        )
    commit = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    files = (
        subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z", "--", str(PACKAGE)])
        .decode()
        .split("\0")
    )
    payload = {}
    for name in filter(None, files):
        source = ROOT / name
        relative = PurePosixPath(name).relative_to(PACKAGE)
        if (
            source.is_symlink()
            or source.suffix not in {".py", ".json", ".png", ".js"}
            or ".." in relative.parts
        ):
            raise ValueError(f"Unsafe/unexpected runtime package member: {relative}")
        payload[str(relative)] = source.read_bytes()
    if not REQUIRED <= payload.keys():
        raise ValueError("Candidate is missing required tracked runtime files")
    payload["LICENSE"] = (ROOT / "LICENSE").read_bytes()
    version = json.loads(payload["manifest.json"])["version"]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archives = {}
    for filename, prefix in ((f"{DOMAIN}.zip", ""), (f"{DOMAIN}-manual.zip", str(PACKAGE) + "/")):
        destination = output / filename
        with zipfile.ZipFile(
            destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, content in sorted(payload.items()):
                entry = zipfile.ZipInfo(prefix + name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, content, compresslevel=9)
        archives[filename] = hashlib.sha256(destination.read_bytes()).hexdigest()
    report = {
        "version": version,
        "commit": commit,
        "dirty": dirty,
        "published": False,
        "archives": archives,
        "runtime_files": {
            name: hashlib.sha256(content).hexdigest() for name, content in sorted(payload.items())
        },
    }
    (output / "BUILD_MANIFEST.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in archives.items())
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.output, allow_dirty=args.allow_dirty), indent=2))
