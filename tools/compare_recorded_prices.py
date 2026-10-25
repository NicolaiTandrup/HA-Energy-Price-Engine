"""Strict offline final-price comparison; no live broker, unit guessing or zero fill."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from math import isfinite
from pathlib import Path


def instant(text):
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise ValueError("Recorded timestamps must include UTC offsets")
    return value.astimezone(UTC)


def capture(value, selected_site):
    if value.get("site_id") != selected_site:
        raise ValueError("Recorded site differs from the explicit comparison mapping")
    if (
        value.get("currency") != "DKK"
        or value.get("unit") != "DKK/kWh"
        or value.get("vat_included") is not True
    ):
        raise ValueError("Recorded final prices must explicitly declare inclusive DKK/kWh")
    result = {}
    for row in value["slots"]:
        start, end = instant(row["start"]), instant(row["end"])
        amount = row["final_price_incl_vat"]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount):
            raise ValueError("Missing/nonfinite/boolean prices cannot become zero")
        if start.timestamp() % 900 or end - start != timedelta(minutes=15) or start in result:
            raise ValueError("Recorded slots must be unique UTC quarters")
        result[start] = amount
    return result


def compare(legacy, candidate, *, legacy_site, candidate_site, start, end, tolerance=1e-6):
    if not isfinite(tolerance) or tolerance < 0:
        raise ValueError("Tolerance must be finite and nonnegative DKK/kWh")
    start, end = instant(start), instant(end)
    if end <= start or start.timestamp() % 900 or end.timestamp() % 900:
        raise ValueError("Select an explicit positive quarter-aligned comparison range")
    left, right = capture(legacy, legacy_site), capture(candidate, candidate_site)
    expected = []
    while start < end:
        expected.append(start)
        start += timedelta(minutes=15)
    common = [s for s in expected if s in left and s in right]
    differences = [abs(left[s] - right[s]) for s in common]
    mismatches = sum(d > tolerance for d in differences)
    missing_left = sum(s not in left for s in expected)
    missing_right = sum(s not in right for s in expected)
    return {
        "offline_only": True,
        "passed": not (mismatches or missing_left or missing_right),
        "expected_slots": len(expected),
        "compared_slots": len(common),
        "mismatches": mismatches,
        "missing_legacy": missing_left,
        "missing_candidate": missing_right,
        "max_absolute_difference_dkk_kwh": max(differences, default=None),
        "tolerance_dkk_kwh": tolerance,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--legacy-site", required=True)
    parser.add_argument("--candidate-site", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args()
    try:
        report = compare(
            json.loads(args.legacy.read_text()),
            json.loads(args.candidate.read_text()),
            legacy_site=args.legacy_site,
            candidate_site=args.candidate_site,
            start=args.start,
            end=args.end,
            tolerance=args.tolerance,
        )
    except (ValueError, KeyError, TypeError, OSError) as err:
        parser.exit(2, str(err) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
