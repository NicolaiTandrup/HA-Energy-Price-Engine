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
    retained = []
    for rule in result.get("dated_components", []):
        if rule["id"] not in {"supplier", "supplier_subscription"} or rule["valid_to"] <= today:
            retained.append(rule)
        elif rule["valid_from"] < today:
            retained.append({**rule, "valid_to": today})
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
    result.pop("provisional_supplier", None)
    if provisional:
        result["provisional_supplier"] = {**rate, "approved": True, "approved_on": today}
    else:
        retained.append(rate)
    if monthly is not None:
        retained.append(
            {**rate, "id": "supplier_subscription", "amount": monthly, "unit": "DKK/month"}
        )
    result["dated_components"] = retained
    return validate_site(result)
