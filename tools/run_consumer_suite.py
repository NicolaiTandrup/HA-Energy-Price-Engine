"""Run a pinned consumer's unchanged full suite against this producer with isolated disk."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from prepare_consumer_refs import PINS

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer", choices=PINS, required=True)
    args = parser.parse_args()
    reference = ROOT / "consumer-references" / args.consumer
    assert (reference / "SOURCE_COMMIT").read_text().strip() == PINS[args.consumer], (
        "Prepare references first"
    )
    node = subprocess.check_output(["node", "--version"], text=True).strip()
    if int(node.lstrip("v").split(".")[0]) < 24:
        raise RuntimeError(
            "Node.js 24+ is required for existing consumer parity tests; do not skip them"
        )
    with tempfile.TemporaryDirectory(prefix="pe-consumer-suite-") as directory:
        plugin = Path(directory) / "pe_disk_isolation.py"
        plugin.write_text(
            "import tempfile\nimport pytest\n"
            "@pytest.hookimpl(hookwrapper=True)\n"
            "def pytest_fixture_setup(fixturedef, request):\n"
            "    outcome = yield\n"
            "    if fixturedef.argname == 'hass_config_dir':\n"
            "        path = tempfile.mkdtemp(prefix='ha-', dir=" + repr(directory) + ")\n"
            "        fixturedef.cached_result = (path, fixturedef.cached_result[1], None)\n"
            "        outcome.force_result(path)\n"
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join((directory, str(reference)))
        environment["PRICE_ENGINE_SOURCE"] = str(ROOT)
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "pe_disk_isolation",
                "--cov=custom_components.ev_charge_manager",
                "--cov-report=term",
                "-W",
                "error::ResourceWarning",
            ],
            cwd=reference,
            env=environment,
        )
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
