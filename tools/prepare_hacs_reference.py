"""Export pinned upstream HACS workflow code as an isolated test dependency."""

import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "stable": "c0dfd8b44297c3673c21973e2539375a53687a9c",
    "upstream": "a15e87ec0d1c82e58f1ddbaf17669d3eaa261eb8",
}


def prepare():
    with tempfile.TemporaryDirectory(prefix="pe-hacs-git-") as directory:
        git = Path(directory) / "reference.git"
        subprocess.run(["git", "init", "--bare", str(git)], check=True, capture_output=True)
        for name, sha in PINS.items():
            target = ROOT / "hacs-references" / name
            marker = target / "SOURCE_COMMIT"
            if target.exists():
                if marker.exists() and marker.read_text().strip() == sha:
                    continue
                raise RuntimeError("Preserve mismatched HACS reference before rebuilding")
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(git),
                    "fetch",
                    "--depth=1",
                    "https://github.com/hacs/integration.git",
                    sha,
                ],
                check=True,
                capture_output=True,
            )
            archive = Path(directory) / (name + ".tar")
            with archive.open("wb") as handle:
                subprocess.run(["git", "-C", str(git), "archive", sha], stdout=handle, check=True)
            target.mkdir(parents=True)
            with tarfile.open(archive) as handle:
                handle.extractall(target, filter="data")
            marker.write_text(sha + "\n")
            print(f"Prepared HACS {name}: {sha}")


if __name__ == "__main__":
    prepare()
