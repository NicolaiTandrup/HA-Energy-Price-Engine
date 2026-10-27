"""Read-only costing of supplied quarter-hour energy, never charging planning/control."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from .models import utc
from .money import decimal_amount


def estimate_charging_cost(
    api, site_id, allocations, *, energy_kind, now=None, producer_entry_id=None
):
    """Cost complete measured/planned allocations using verified API v1 prices only.

    The caller (normally CM) owns energy measurement/allocation and session planning.
    Missing energy or prices are not zero. Nothing is written, scheduled or commanded.
    """
    if energy_kind not in {"measured", "planned"} or not allocations:
        raise ValueError("Provide measured or planned energy for every session quarter")
    now = utc(now or datetime.now(UTC))
    energy = []
    for start, kwh in allocations:
        start = utc(start)
        if start.timestamp() % 900:
            raise ValueError("Energy allocations must start on an aware 15-minute boundary")
        if energy_kind == "measured" and start > now:
            raise ValueError("Measured energy cannot belong to a future quarter")
        amount = Decimal(decimal_amount(kwh))
        if energy and start != energy[-1][0] + timedelta(minutes=15):
            raise ValueError(
                "Provide consecutive quarters, including explicit zero-energy quarters"
            )
        energy.append((start, amount))
    result = api.lookup(
        site_id,
        energy[0][0],
        energy[-1][0] + timedelta(minutes=15),
        now=now,
        producer_entry_id=producer_entry_id,
    )
    report = {
        "price_status": str(result.status),
        "energy_kind": energy_kind,
        "estimated_cost_dkk": None,
        "energy_kwh": str(sum((kwh for _, kwh in energy), Decimal(0))),
        "fixed_subscriptions_included": False,
        "is_settled_accounting": False,
        "reason": result.reason,
        "quarters": [],
    }
    if str(result.status) != "READY":
        return report
    if len(result.records) != len(energy):
        raise ValueError("Verified prices do not cover the supplied energy allocations")
    total = Decimal(0)
    for (start, kwh), record in zip(energy, result.records, strict=True):
        if record.start != start or record.end != start + timedelta(minutes=15):
            raise ValueError("Verified quarter does not match its energy allocation")
        cost = kwh * Decimal(str(record.final_price_incl_vat))
        total += cost
        report["quarters"].append(
            {
                "start": start.isoformat(),
                "energy_kwh": str(kwh),
                "price_dkk_per_kwh": record.final_price_incl_vat,
                "revision": record.revision,
                "estimated_cost_dkk": str(cost),
            }
        )
    report["estimated_cost_dkk"] = str(total)
    return report
