"""Measure synthetic ledger storage/lookup costs; never contact an HA installation.

Use the locked environment: python tools/benchmark_ledger.py --years 1 --output /tmp/result.json
Host results are not Raspberry Pi hardware measurements. Each run uses a fresh
TemporaryDirectory, independent HA core object and fictional rates/provenance.
"""

import argparse
import asyncio
import json
import resource
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.core import HomeAssistant

from custom_components.ha_energy_price_engine.models import PriceSlot
from custom_components.ha_energy_price_engine.price_engine import PriceEngine


def fictional_tariff():
    return {
        "mode": "spot_ex_vat",
        "vat": 0.25,
        "timezone": "Europe/Copenhagen",
        "components": [
            {
                "id": name,
                "amount": amount,
                "unit": "DKK/kWh",
                "vat_rate": 0.25,
                "vat_included": False,
                "valid_from": "2010-01-01",
                "valid_to": "2050-01-01",
                "source": "Fictional benchmark only",
                "verified_on": "2026-10-24",
                "locked": True,
            }
            for name, amount in [
                ("supplier", 0.1),
                ("dso", 0.2),
                ("energinet_net", 0.04),
                ("energinet_system", 0.07),
                ("electricity_tax", 0.008),
            ]
        ],
    }


async def run(years):
    with tempfile.TemporaryDirectory(prefix="pe-benchmark-") as directory:
        hass = HomeAssistant(directory)
        engine = PriceEngine(hass, "synthetic")
        base = datetime(2020, 1, 1, tzinfo=UTC)
        now = base - timedelta(days=1)
        count = 365 * years * 96
        slots = tuple(
            PriceSlot(
                base + timedelta(minutes=15 * i),
                base + timedelta(minutes=15 * (i + 1)),
                (i % 10000) / 10000 - 0.2,
            )
            for i in range(count)
        )
        tick = time.perf_counter()
        await engine.async_update(
            "synthetic",
            slots,
            fictional_tariff(),
            {"provider": "synthetic-benchmark", "verified_at": now.isoformat()},
            now,
        )
        initial = time.perf_counter() - tick
        point = slots[-1].end
        more = tuple(
            PriceSlot(
                point + timedelta(minutes=15 * i), point + timedelta(minutes=15 * (i + 1)), 0.5
            )
            for i in range(96)
        )
        tick = time.perf_counter()
        await engine.async_update(
            "synthetic",
            more,
            fictional_tariff(),
            {"provider": "synthetic-benchmark", "verified_at": now.isoformat()},
            now,
        )
        append = time.perf_counter() - tick
        tick = time.perf_counter()
        restored = PriceEngine(hass, "synthetic")
        await restored.async_load(["synthetic"])
        reload = time.perf_counter() - tick
        tick = time.perf_counter()
        for _ in range(1000):
            result = restored.lookup("synthetic", more[0].start, more[-1].end)
            assert len(result) == 96
        query = (time.perf_counter() - tick) / 1000
        data = {
            "synthetic": True,
            "hardware": "cloud Linux x86_64; not Raspberry Pi",
            "years": years,
            "records": count + 96,
            "initial_seconds": initial,
            "append_96_seconds": append,
            "reload_seconds": reload,
            "lookup_96_mean_seconds": query,
            "storage_bytes": sum(
                p.stat().st_size for p in Path(directory).rglob("*") if p.is_file()
            ),
            "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
        await hass.async_stop()
        return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, choices=range(1, 11), default=1)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    data = asyncio.run(run(options.years))
    encoded = json.dumps(data, indent=2) + "\n"
    if options.output:
        options.output.write_text(encoded)
    print(encoded)
