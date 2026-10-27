"""Date-aware, separately verified and VAT-normalized marginal components."""

from datetime import date
from math import isfinite
from zoneinfo import ZoneInfo

from .money import per_kwh

REQUIRED = {"energinet_net", "energinet_system", "electricity_tax", "supplier"}


class MissingPriceComponents(ValueError):
    """Structured corrective guidance without changing calculation/fail-closed rules."""

    def __init__(self, components, local):
        self.components = sorted(components)
        self.period = local.isoformat()
        self.action = "Open Configure and enter the supplier markup or confirm the grid product. For expired public charges, add verified effective rates under Advanced. Save the step, then Check prices."
        super().__init__(
            f"Missing verified{' DSO' if self.components == ['dso'] else ''} components: {', '.join(self.components)} for {self.period}. {self.action} Prices remain unavailable, never zero."
        )


def danish_public_components():
    """Issue #8 verified policy periods only; never extrapolate unknown years.

    The owner supplied these 2026/2027 rates in #8. This is a dated policy adapter,
    not a claim of live legislation scraping or a customer's supplier contract.
    """
    result = []
    for name, amount, end in [
        ("energinet_net", 4.3, "2027-01-01"),
        ("energinet_system", 7.2, "2027-01-01"),
        ("electricity_tax", 0.8, "2028-01-01"),
    ]:
        result.append(
            {
                "id": name,
                "amount": amount,
                "unit": "ore/kWh",
                "vat_included": False,
                "vat_rate": 0.25,
                "valid_from": "2026-01-01",
                "valid_to": end,
                "source": "Rate specified by owner: Manager issue #8",
                "verified_on": "2026-10-23",
                "eligibility": "all",
            }
        )
    return result


def active_hours(rule):
    hours = rule.get("hours", [])
    if not isinstance(hours, list) or any(
        isinstance(v, bool) or not str(v).isdigit() or not 0 <= int(v) <= 23 for v in hours
    ):
        raise ValueError("Hours must be a list of local clock hours 0–23")
    return frozenset(map(int, hours)) if hours else frozenset(range(24))


def normalize_component(rule):
    if isinstance(rule["amount"], bool) or isinstance(rule["vat_rate"], bool):
        raise ValueError("Boolean values are not money or VAT rates")
    amount = float(rule["amount"])
    rate = float(rule["vat_rate"])
    if not isfinite(amount) or amount < 0 or not isfinite(rate) or not 0 <= rate <= 1:
        raise ValueError("Invalid component amount/VAT")
    if (
        rule["unit"] not in {"DKK/kWh", "ore/kWh", "DKK/month"}
        or type(rule["vat_included"]) is not bool
    ):
        raise ValueError("Explicit component unit and VAT inclusion required")
    if (
        not isinstance(rule.get("source"), str)
        or not rule["source"].strip()
        or not rule.get("verified_on")
    ):
        raise ValueError("Component source and verification date required")
    date.fromisoformat(rule["verified_on"])
    hours = active_hours(rule)
    amount = per_kwh(rule["amount"], rule["unit"])
    ex = amount / (1 + rate) if rule["vat_included"] else amount
    gross = amount if rule["vat_included"] else amount * (1 + rate)
    return {
        "id": rule["id"],
        "hours": sorted(hours) if rule.get("hours") else [],
        "unit": "DKK/month" if rule["unit"] == "DKK/month" else "DKK/kWh",
        "ex_vat": ex,
        "vat": gross - ex,
        "incl_vat": gross,
        "source": rule["source"],
        "valid_from": rule["valid_from"],
        "valid_to": rule["valid_to"],
        "verified_on": rule["verified_on"],
        "locked": rule.get("locked", False),
        "eligibility": rule.get("eligibility", "all"),
    }


def validate_rules(rules):
    if not isinstance(rules, list):
        raise ValueError("Dated component rules must be a list")
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("Invalid dated rule")
        normalize_component(rule)
        if date.fromisoformat(rule["valid_to"]) <= date.fromisoformat(rule["valid_from"]):
            raise ValueError("Invalid component effective range")


def eligible(rule, tariff, day):
    """Shared dated eligibility predicate for composition and setup diagnostics."""
    if rule.get("eligibility", "all") == "heating_above_4000":
        if not isfinite(float(tariff.get("annual_usage_kwh", 0))):
            raise ValueError("Invalid verified annual usage")
        return bool(
            tariff.get("heating_registered")
            and tariff.get("usage_year") == day.year
            and tariff.get("annual_usage_kwh", 0) > 4000
        )
    if rule.get("eligibility", "all") != "all":
        raise ValueError("Unverified eligibility class")
    return True


def compose_dated(slot, tariff):
    if tariff.get("mode") not in {"spot_ex_vat", "spot_incl_vat"}:
        raise ValueError("Dated components cannot be added to all-in input")
    if any(tariff.get(key, 0) for key in ("tax", "supplier")):
        raise ValueError("Dated and legacy tax/supplier fees would be duplicated")
    active, fixed = resolved_rules(slot, tariff)
    local = slot.start.astimezone(ZoneInfo(tariff.get("timezone", "Europe/Copenhagen")))
    if not REQUIRED <= active.keys():
        raise MissingPriceComponents(REQUIRED - active.keys(), local)
    vat = float(tariff["vat"])
    if not isfinite(vat) or not 0 <= vat <= 1:
        raise ValueError("Invalid spot/grid VAT")
    spot_ex = slot.price / (1 + vat) if tariff["mode"] == "spot_incl_vat" else slot.price
    manual_dso = active.get("dso")
    if not manual_dso or (not manual_dso["locked"] and "grid_slots" in tariff):
        if "grid" not in tariff and "grid_slots" not in tariff:
            raise MissingPriceComponents({"dso"}, local)
        grid = float(tariff.get("grid", 0))
        if "grid_slots" in tariff:
            matching = [
                s for s in tariff["grid_slots"] if s.start <= slot.start and s.end >= slot.end
            ]
            if len(matching) != 1:
                raise ValueError("Missing/overlapping grid tariff")
            grid += matching[0].price
        if not isfinite(grid) or grid < 0:
            raise ValueError("Invalid grid component")
        active["dso"] = {
            "id": "dso",
            "ex_vat": grid,
            "vat": grid * vat,
            "incl_vat": grid * (1 + vat),
        }
    active["spot"] = {
        "id": "spot",
        "ex_vat": spot_ex,
        "vat": spot_ex * vat,
        "incl_vat": slot.price if tariff["mode"] == "spot_incl_vat" else slot.price * (1 + vat),
    }
    return sum(c["incl_vat"] for c in active.values()), {
        "components": active,
        "fixed_subscriptions_excluded": fixed,
    }


def resolved_rules(slot, tariff):
    """Canonical active dated rules, also used by component diagnostics."""
    local = slot.start.astimezone(ZoneInfo(tariff.get("timezone", "Europe/Copenhagen")))
    day = local.date()
    rules = tariff["components"]
    if not isinstance(rules, list):
        raise ValueError("Dated components must be a list")
    active = {}
    fixed = []
    for rule in rules:
        start, end = date.fromisoformat(rule["valid_from"]), date.fromisoformat(rule["valid_to"])
        if end <= start:
            raise ValueError("Invalid component effective period")
        if not start <= day < end or local.hour not in active_hours(rule):
            continue
        if not eligible(rule, tariff, day):
            continue
        component = normalize_component(rule)
        if rule["unit"] == "DKK/month":
            fixed.append(component)
            continue
        name = rule["id"]
        if name in active:
            previous = active[name]
            score = (component["locked"], component["eligibility"] == "heating_above_4000")
            old_score = (previous["locked"], previous["eligibility"] == "heating_above_4000")
            if score == old_score:
                raise ValueError("Overlapping component rate versions")
            if score < old_score:
                continue
        active[name] = component
    return active, fixed
