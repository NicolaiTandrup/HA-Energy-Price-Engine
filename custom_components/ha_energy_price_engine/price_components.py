"""Date-aware, separately verified and VAT-normalized marginal components."""

from datetime import date, datetime
from math import isfinite
from zoneinfo import ZoneInfo

from .const import COMPONENTS
from .models import utc
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
    if rule["unit"] not in {"DKK/kWh", "ore/kWh"} or type(rule["vat_included"]) is not bool:
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
        "unit": "DKK/kWh",
        "ex_vat": ex,
        "vat": gross - ex,
        "incl_vat": gross,
        "source": rule["source"],
        "valid_from": rule["valid_from"],
        "valid_to": rule["valid_to"],
        "verified_on": rule["verified_on"],
        "locked": rule.get("locked", False),
        **({"effective_after": rule["effective_after"]} if rule.get("effective_after") else {}),
    }


def validate_rules(rules):
    if not isinstance(rules, list):
        raise ValueError("Dated component rules must be a list")
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("Invalid dated rule")
        allowed = {
            "id",
            "amount",
            "unit",
            "vat_included",
            "vat_rate",
            "valid_from",
            "valid_to",
            "source",
            "verified_on",
            "hours",
            "effective_after",
            "locked",
        }
        if set(rule) - allowed or rule.get("id") not in COMPONENTS:
            raise ValueError("Unsupported marginal component or retired rule fields")
        normalize_component(rule)
        if boundary := rule.get("effective_after"):
            if utc(datetime.fromisoformat(boundary)).timestamp() % 900:
                raise ValueError("Rate boundary must align to a quarter")
        if date.fromisoformat(rule["valid_to"]) <= date.fromisoformat(rule["valid_from"]):
            raise ValueError("Invalid component effective range")


def compose_dated(slot, tariff):
    if tariff.get("mode") != "spot_ex_vat":
        raise ValueError("Dated components cannot be added to all-in input")
    active = resolved_rules(slot, tariff)
    local = slot.start.astimezone(ZoneInfo(tariff.get("timezone", "Europe/Copenhagen")))
    if not REQUIRED <= active.keys():
        raise MissingPriceComponents(REQUIRED - active.keys(), local)
    vat = float(tariff["vat"])
    if not isfinite(vat) or not 0 <= vat <= 1:
        raise ValueError("Invalid spot/grid VAT")
    spot_ex = slot.price
    dso = resolved_dso(slot, tariff, active)
    if dso is None:
        raise MissingPriceComponents({"dso"}, local)
    active["dso"] = dso
    active["spot"] = {
        "id": "spot",
        "ex_vat": spot_ex,
        "vat": spot_ex * vat,
        "incl_vat": slot.price * (1 + vat),
    }
    return sum(c["incl_vat"] for c in active.values()), {
        "components": active,
    }


def resolved_rules(slot, tariff):
    """Canonical active dated rules, also used by component diagnostics."""
    local = slot.start.astimezone(ZoneInfo(tariff.get("timezone", "Europe/Copenhagen")))
    day = local.date()
    rules = tariff["components"]
    if not isinstance(rules, list):
        raise ValueError("Dated components must be a list")
    active = {}
    for rule in rules:
        start, end = date.fromisoformat(rule["valid_from"]), date.fromisoformat(rule["valid_to"])
        if end <= start:
            raise ValueError("Invalid component effective period")
        if not start <= day < end or local.hour not in active_hours(rule):
            continue
        if rule.get("effective_after") and slot.start < utc(
            datetime.fromisoformat(rule["effective_after"])
        ):
            continue
        component = normalize_component(rule)
        name = rule["id"]
        if name in active:
            previous = active[name]
            score = component["locked"]
            old_score = previous["locked"]
            if score == old_score:
                raise ValueError("Overlapping component rate versions")
            if score < old_score:
                continue
        active[name] = component
    return active


def resolved_dso(slot, tariff, active=None):
    """The same verified grid component for pricing and the update-time grid cache."""
    active = (
        active
        if active is not None
        else resolved_rules(
            slot, {**tariff, "components": [r for r in tariff["components"] if r["id"] == "dso"]}
        )
    )
    if "dso" in active:
        return active["dso"]
    matching = [
        s for s in tariff.get("grid_slots", []) if s.start <= slot.start and s.end >= slot.end
    ]
    if "grid_slots" in tariff and len(matching) != 1:
        raise ValueError("Missing/overlapping grid tariff")
    if not matching:
        return None
    value = matching[0].price
    if value < 0 or not isfinite(value):
        raise ValueError("Invalid grid component")
    vat = tariff["vat"]
    return {
        "id": "dso",
        "ex_vat": value,
        "vat": value * vat,
        "incl_vat": value * (1 + vat),
        "source": "Verified Radius C Datahub tariff",
    }
