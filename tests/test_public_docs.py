"""Public installation docs remain suitable for ordinary users."""

import re
from pathlib import Path


def test_public_guides_do_not_publish_private_test_hosts_or_internal_workflows():
    root = Path(__file__).parents[1]
    for name in (
        "README.md",
        "docs/BETA_SETUP.md",
        "docs/WIZARD_GUIDE.md",
        "docs/HACS_DISTRIBUTION.md",
        "docs/BETA_ACCEPTANCE.md",
    ):
        content = (root / name).read_text()
        assert not re.search(r"PAHA\d|192\.168\.|10\.\d+\.\d+\.\d+|EV PR|PR #\d+", content), name
    assert "CONTRIBUTING.md" in (root / "README.md").read_text()
