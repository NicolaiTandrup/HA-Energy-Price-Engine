"""User-confirmed current supplier settings; dated internals stay out of ordinary UI."""

from copy import deepcopy
from datetime import UTC, datetime
from math import ceil
from zoneinfo import ZoneInfo

from .configuration import validate_site

OPEN_END = "9999-12-31"


def current_contract(
    site, amount, vat_included, monthly, provisional, now, *, source, product="custom"
):
    """Replace future supplier coverage, retain historical rules/settled ledger rows.

    New unknown intervals are never backfilled with today's newly confirmed rate.
    The next complete UTC quarter is the first writable interval. No time-zone
    clock arithmetic is used at a DST fold.
    """
    result = deepcopy(site)
    activation = datetime.fromtimestamp(ceil(now.timestamp() / 900) * 900, UTC)
    today = str(now.astimezone(ZoneInfo(site["timezone"])).date())
    result.update(supplier_product=product, pricing_start=activation.isoformat())
    rate = {
        "id": "supplier",
        "amount": amount,
        "unit": "ore/kWh",
        "vat_included": vat_included,
        "vat_rate": site["vat"],
        "valid_from": today,
        "valid_to": OPEN_END,
        "source": source,
        "verified_on": today,
        "locked": True,
        "eligibility": "all",
        "confirmed_at": now.isoformat(),
    }
    retained, segments = replace_current_rules(result.get("dated_components", []), rate, today)
    result.pop("provisional_supplier", None)
    if provisional:
        result["provisional_supplier"] = {**rate, "approved": True, "approved_on": today}
    else:
        retained.extend(segments)
    subscription = {
        **rate,
        "id": "supplier_subscription",
        "amount": monthly or 0,
        "unit": "DKK/month",
    }
    retained, subscriptions = replace_current_rules(retained, subscription, today)
    if monthly is not None:
        retained.extend(subscriptions)
    result["dated_components"] = retained
    return validate_site(result)


def replace_current_rules(rules, new_rule, today):
    """Retain scheduled overrides, fill uncovered date/hour ranges with current terms."""
    from .price_components import active_hours

    retained = []
    future = []
    for old in rules:
        if old["id"] != new_rule["id"] or old["valid_to"] <= today:
            retained.append(old)
        elif old["valid_from"] > today:
            retained.append(old)
            future.append(old)
        elif old["valid_from"] < today:
            retained.append({**old, "valid_to": today})
    boundaries = sorted(
        {today, OPEN_END} | {r[k] for r in future for k in ("valid_from", "valid_to")}
    )
    segments = []
    for start, end in zip(boundaries, boundaries[1:]):
        blocked = set().union(
            *(
                active_hours(r)
                for r in future
                if r["valid_from"] <= start < r["valid_to"] and r.get("eligibility", "all") == "all"
            )
        )
        hours = sorted(set(range(24)) - blocked)
        if hours:
            rule = {**new_rule, "valid_from": start, "valid_to": end}
            if len(hours) < 24:
                rule["hours"] = hours
            segments.append(rule)
    return retained, segments
