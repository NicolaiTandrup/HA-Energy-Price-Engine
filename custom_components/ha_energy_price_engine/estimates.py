"""Explicitly approved visualization estimates. Never stored in the price ledger/API."""

from copy import deepcopy

from .models import PriceSlot
from .price_engine import calculate


def estimate(site, slots, tariff, source, now):
    provisional = site.get("provisional_supplier")
    if not provisional or not provisional.get("approved") or not slots:
        return ()
    # Only fresh verified public inputs may be combined with an unverified contract.
    if source.get("dso", {}).get("warning"):
        return ()
    draft = deepcopy(tariff)
    rule = {
        **provisional,
        "id": "supplier",
        "eligibility": "all",
        "locked": True,
        "verified_on": provisional["approved_on"],
        "source": "user_approved_provisional_NOT_verified",
    }
    draft["components"] = [r for r in draft.get("components", []) if r["id"] != "supplier"] + [rule]
    try:
        records = calculate(site["id"], slots, draft, {**source, "estimated": True}, now, 0)
    except ValueError, TypeError, KeyError:
        return ()
    return tuple(PriceSlot(r.start, r.end, r.final_price_incl_vat) for r in records)
