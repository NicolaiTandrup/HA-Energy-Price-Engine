"""One Danish price-site schema: official source and dated marginal rates."""

import re
from copy import deepcopy
from datetime import UTC, datetime
from math import ceil, isfinite
from zoneinfo import ZoneInfo

from .const import COMPONENTS
from .price_components import active_hours, danish_public_components, validate_rules


def settings(entry):
    return {**entry.data, **entry.options}


def validate_site(value):
    site = deepcopy(value)
    allowed = {
        "id",
        "name",
        "nordpool_entry",
        "area",
        "timezone",
        "vat",
        "dso_mode",
        "dated_components",
        "setup_step",
    }
    if set(site) - allowed:
        raise ValueError(
            "Retired or unsupported settings; reset the beta site before using the MVP"
        )
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]{0,63}", site["id"]):
        raise ValueError("Invalid site identity")
    if not site["name"].strip() or not site["nordpool_entry"]:
        raise ValueError("Site name and official Nord Pool source are required")
    if site["area"] not in {"DK1", "DK2"}:
        raise ValueError("The Danish MVP supports DK1 and DK2")
    site.setdefault("timezone", "Europe/Copenhagen")
    ZoneInfo(site["timezone"])
    if site["timezone"] != "Europe/Copenhagen":
        raise ValueError("DK1/DK2 use Europe/Copenhagen")
    vat = float(site.setdefault("vat", 0.25))
    if not isfinite(vat) or not 0 <= vat <= 1:
        raise ValueError("Invalid VAT fraction")
    site["vat"] = vat
    if site.setdefault("dso_mode", "manual") not in {"manual", "radius_c"}:
        raise ValueError("Confirm Radius C or supply a manual grid rate")
    rules = site.setdefault("dated_components", [])
    validate_rules(rules)
    for i, rule in enumerate(rules):
        if rule["id"] not in COMPONENTS:
            raise ValueError("Only marginal electricity components are supported")
        for other in rules[:i]:
            if (
                rule["id"] == other["id"]
                and active_hours(rule) & active_hours(other)
                and max(rule["valid_from"], other["valid_from"])
                < min(rule["valid_to"], other["valid_to"])
            ):
                raise ValueError("Overlapping manual rates; edit the existing period")
    return site


def tariff_for(site):
    return {
        "mode": "spot_ex_vat",
        "vat": site["vat"],
        "components": danish_public_components()
        + [{**r, "locked": True} for r in site["dated_components"]],
        "timezone": site["timezone"],
    }


def current_rate(site, component, amount, vat_included, now, *, whole_day=False):
    """Confirm a from-now marginal rate, preserving scheduled date/hour overrides.

    Date coverage alone cannot turn a newly confirmed rate into historical fact.
    effective_after is the next complete UTC quarter; Advanced can explicitly
    confirm whole-date coverage instead. Existing past price records stay immutable.
    """
    today = str(now.astimezone(ZoneInfo(site["timezone"])).date())
    from datetime import date

    from .price_engine import day_bounds

    boundary = (
        day_bounds(date.fromisoformat(today), site["timezone"])[0]
        if whole_day
        else datetime.fromtimestamp(ceil(now.timestamp() / 900) * 900, UTC)
    )
    rate = {
        "id": component,
        "amount": amount,
        "unit": "ore/kWh",
        "vat_included": vat_included,
        "vat_rate": site["vat"],
        "valid_from": today,
        "valid_to": "9999-12-31",
        "effective_after": boundary.isoformat(),
        "source": "User-confirmed marginal rate",
        "verified_on": today,
    }
    retained, future = [], []
    for old in site["dated_components"]:
        if old["id"] != component or old["valid_to"] <= today:
            retained.append(old)
        elif old["valid_from"] > today:
            retained.append(old)
            future.append(old)
        elif old["valid_from"] < today:
            retained.append({**old, "valid_to": today})
    boundaries = sorted(
        {today, "9999-12-31"} | {r[k] for r in future for k in ("valid_from", "valid_to")}
    )
    for start, end in zip(boundaries, boundaries[1:]):
        blocked = set().union(
            *(active_hours(r) for r in future if r["valid_from"] <= start < r["valid_to"])
        )
        hours = sorted(set(range(24)) - blocked)
        if hours:
            retained.append(
                {
                    **rate,
                    "valid_from": start,
                    "valid_to": end,
                    **({"hours": hours} if len(hours) < 24 else {}),
                }
            )
    return validate_site({**site, "dated_components": retained})
