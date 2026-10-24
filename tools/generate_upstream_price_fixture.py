"""Generate offline golden values from the pinned EV Manager PR #12 source.

Run with the locked Python environment and a disposable source checkout:
  .venv/bin/python tools/generate_upstream_price_fixture.py /path/to/source
This does not access a live service. Never regenerate expected values from the
producer under test. Provenance is embedded in the resulting fixture.
"""

import importlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from types import ModuleType

SOURCE_COMMIT = "9d949c6d0905646d1bbf973ea2edb47846e1607d"
source = Path(sys.argv[1]).resolve()
head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
if head != SOURCE_COMMIT:
    raise SystemExit(f"Expected pinned upstream {SOURCE_COMMIT}, got {head}")
package = ModuleType("upstream_price_reference")
package.__path__ = [str(source / "custom_components/ev_charge_manager")]
sys.modules[package.__name__] = package
models = importlib.import_module(f"{package.__name__}.planner")
components = importlib.import_module(f"{package.__name__}.price_components")
tariffs = importlib.import_module(f"{package.__name__}.tariff_source")
engine = importlib.import_module(f"{package.__name__}.price_engine")
root = Path(__file__).resolve().parents[1]
radius = json.loads((root / "tests/fixtures/radius_c_datahub.json").read_text())
scenarios = []
for day in (date(2026, 3, 29), date(2026, 6, 15), date(2026, 10, 24), date(2026, 10, 25)):
    start, end = engine.day_bounds(day)
    grid, provenance = tariffs.normalize_tariffs(
        radius, tariffs.RADIUS_GLN, tariffs.RADIUS_CODE, start, end
    )
    supplier = {
        "id": "supplier",
        "amount": 0.030 if day.month == 6 else 0.11,
        "unit": "DKK/kWh",
        "vat_included": False,
        "vat_rate": 0.25,
        "valid_from": "2026-06-01" if day.month == 6 else "2026-01-01",
        "valid_to": "2026-10-01" if day.month == 6 else "2027-01-01",
        "source": "Documented historical household example"
        if day.month == 6
        else "Fictional parity supplier",
        "verified_on": "2026-10-24",
        "locked": True,
    }
    for inclusive in (False, True):
        tariff = {
            "mode": "spot_incl_vat" if inclusive else "spot_ex_vat",
            "vat": 0.25,
            "timezone": "Europe/Copenhagen",
            "components": components.danish_public_components() + [supplier],
        }
        expected = []
        for i, g in enumerate(grid):
            raw_ex = ((i % 13) - 4) / 10
            raw = raw_ex * 1.25 if inclusive else raw_ex
            slot = models.PriceSlot(g.start, g.end, raw)
            final, _ = components.compose_dated(slot, {**tariff, "grid_slots": grid})
            expected.append(
                {
                    "start": slot.start.isoformat(),
                    "end": slot.end.isoformat(),
                    "raw": raw,
                    "final": final,
                }
            )
        scenarios.append(
            {
                "day": str(day),
                "site_id": "household_historical" if day.month == 6 else "fictional_parity_site",
                "tariff": tariff,
                "expected": expected,
                "radius_version": provenance["version"],
            }
        )
(root / "tests/fixtures/upstream_price_parity.json").write_text(
    json.dumps(
        {
            "source_repository": "NicolaiTandrup/HA-EV-Charge-Manager",
            "source_commit": head,
            "not_live_broker_parity": True,
            "scenarios": scenarios,
        },
        indent=2,
    )
    + "\n"
)
