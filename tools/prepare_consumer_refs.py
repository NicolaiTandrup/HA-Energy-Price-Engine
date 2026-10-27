"""Export pinned, read-only consumer test dependencies without changing their branches."""

import argparse
import subprocess
import tarfile
import tempfile
from pathlib import Path

PINS = {
    "pr25": "1246ccff25ee36f705e7c503499317f58802d7a2",
    "pr26": "5ef7115a9599e1ff25019e91b3737500853b9a38",
    "pr15": "0a28438d1cfa5cc8136417f1520a891faa67b979",
    "pr16": "23bf84b2488372d9708164a4b42df3fd109b7726",
}
ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/NicolaiTandrup/HA-EV-Charge-Manager.git"


def prepare(source_git=None):
    # The migration test executes the immutable released producer, even in shallow CI.
    for released in (
        "56cdb3c10993179371483812cbc36f651ba3ad8e",
        "0c93d2bfac88878cff46e7726f59accbeababf85",
        "78ef9ba4d02ccb85b9395991d1376fbdec34bb84",
    ):
        if subprocess.run(
            ["git", "cat-file", "-e", released + "^{commit}"], cwd=ROOT, capture_output=True
        ).returncode:
            subprocess.run(
                ["git", "fetch", "--depth=1", "origin", released],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
    output = ROOT / "consumer-references"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pe-consumer-ref-") as temporary:
        cache = Path(source_git) if source_git else Path(temporary) / "reference.git"
        if source_git is None:
            subprocess.run(["git", "init", "--bare", str(cache)], check=True, capture_output=True)
        for name, commit in PINS.items():
            destination = output / name
            marker = destination / "SOURCE_COMMIT"
            if destination.exists():
                if marker.exists() and marker.read_text().strip() == commit:
                    continue
                raise RuntimeError(
                    f"Reference {name} exists with different or unknown contents; preserve it before rebuilding"
                )
            if source_git is None:
                subprocess.run(
                    ["git", "-C", str(cache), "fetch", "--depth=1", REPOSITORY, commit],
                    check=True,
                    capture_output=True,
                )
            actual = subprocess.check_output(
                ["git", "-C", str(cache), "rev-parse", commit + "^{commit}"], text=True
            ).strip()
            if actual != commit:
                raise RuntimeError("Reference commit identity mismatch")
            archive = Path(temporary) / (name + ".tar")
            with archive.open("wb") as handle:
                subprocess.run(
                    ["git", "-C", str(cache), "archive", commit], stdout=handle, check=True
                )
            destination.mkdir()
            with tarfile.open(archive) as handle:
                handle.extractall(destination, filter="data")
            marker.write_text(commit + "\n")
            print(f"Prepared {name} at {commit}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-git",
        type=Path,
        help="Reuse an existing research clone instead of fetching dependencies",
    )
    prepare(parser.parse_args().source_git)
