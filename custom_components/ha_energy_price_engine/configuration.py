"""Validate durable per-site business configuration before accepting UI edits."""

import re
from copy import deepcopy
from zoneinfo import ZoneInfo

from .const import COMPONENTS
from .price_components import danish_public_components, validate_rules
from .sources import BASES, UNIT_MULTIPLIERS


def settings(entry):
    return {**entry.data, **entry.options}


def validate_site(value):
    site = deepcopy(value)
    source_type = site.setdefault("source_type", "nordpool")
    site.setdefault("nordpool_entry", "")
    site.setdefault("price_basis", "spot_ex_vat")
    site.setdefault("price_unit", "DKK/MWh" if source_type == "nordpool" else "DKK/kWh")
    site.setdefault("supplier", "custom")
    site.setdefault("dso_tariff_class", "C")
    if source_type not in {"nordpool", "entity"}:
        raise ValueError("Unsupported source type")
    if source_type == "nordpool":
        if (
            not site["nordpool_entry"]
            or site["price_basis"] != "spot_ex_vat"
            or site["price_unit"] != "DKK/MWh"
        ):
            raise ValueError(
                "Official Nord Pool requires an explicit entry and ex-VAT DKK/MWh basis"
            )
    elif (
        not site.get("price_entity")
        or site["price_basis"] not in BASES
        or site["price_unit"] not in UNIT_MULTIPLIERS
    ):
        raise ValueError("Entity source, explicit unit and price basis are required")
    else:
        site["nordpool_entry"] = ""
        site["price_attribute"] = site.get("price_attribute", "slots")
        site["price_multiplier"] = UNIT_MULTIPLIERS[site["price_unit"]]
    if site.get("supplier") not in {"custom", "ewii"}:
        raise ValueError("Unsupported supplier label; use custom for another supplier")
    if site.get("dso_mode") == "radius_c" and site["dso_tariff_class"] != "C":
        raise ValueError(
            "Only Radius C has verified automatic tariff identity; use dated manual rates for another class"
        )
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]{0,63}", site["id"]):
        raise ValueError("Site ID must be a stable lowercase slug")
    if not site["name"].strip() or not site["area"].strip():
        raise ValueError("Site name, area and official Nord Pool entry are required")
    ZoneInfo(site["timezone"])
    vat = float(site["vat"])
    if not 0 <= vat <= 1:
        raise ValueError("VAT must be a fraction between 0 and 1")
    site["vat"] = vat
    rules = site.get("dated_components", [])
    validate_rules(rules)
    if site["price_basis"] == "all_in" and (
        rules or site.get("danish_public_rates") or site.get("dso_mode", "manual") != "manual"
    ):
        raise ValueError(
            "All-in input already includes tariffs, taxes, supplier and VAT; additions are prohibited"
        )
    for i, rule in enumerate(rules):
        if rule["id"] not in COMPONENTS or rule.get("eligibility", "all") not in {
            "all",
            "heating_above_4000",
        }:
            raise ValueError("Unsupported component or eligibility")
        if rule["id"] == "subscription" and rule["unit"] != "DKK/month":
            raise ValueError("Subscriptions must use DKK/month")
        if rule["id"] != "subscription" and rule["unit"] == "DKK/month":
            raise ValueError("Marginal components require a per-kWh unit")
        for other in rules[:i]:
            if (
                rule["id"] == other["id"]
                and rule.get("locked", False) == other.get("locked", False)
                and rule.get("eligibility", "all") == other.get("eligibility", "all")
                and max(rule["valid_from"], other["valid_from"])
                < min(rule["valid_to"], other["valid_to"])
            ):
                raise ValueError(
                    "Overlapping component periods; edit or remove the old period first"
                )
    if site.get("danish_public_rates"):
        # Presets are dated verified baselines, not inferred future terms.
        for rule in rules:
            if rule["id"] in {r["id"] for r in danish_public_components()} and not rule.get(
                "locked"
            ):
                raise ValueError("Manual overrides of verified presets must be locked")
    if site.get("dso_mode", "manual") not in {"manual", "radius_c"}:
        raise ValueError("Unknown DSO mode")
    if not isinstance(site.get("annual_usage_kwh", 0), (int, float)) or not 0 <= site.get(
        "annual_usage_kwh", 0
    ) < float("inf"):
        raise ValueError("Invalid annual usage")
    return site


def tariff_for(site):
    if site.get("price_basis") == "all_in":
        return {"mode": "all_in"}
    rules = list(site.get("dated_components", []))
    if site.get("danish_public_rates"):
        rules = danish_public_components() + rules
    return {
        "mode": site.get("price_basis", "spot_ex_vat"),
        "vat": site["vat"],
        "components": rules,
        "timezone": site["timezone"],
        "heating_registered": site.get("heating_registered", False),
        "annual_usage_kwh": site.get("annual_usage_kwh", 0),
        "usage_year": site.get("usage_year"),
    }


def household_historical_example():
    """Explicit historical example, never automatically applied to a site."""
    return {
        "id": "supplier",
        "amount": 0.030,
        "unit": "DKK/kWh",
        "vat_included": False,
        "vat_rate": 0.25,
        "valid_from": "2026-06-01",
        "valid_to": "2026-10-01",
        "source": "Owner documented EWII household June–September 2026 invoices; issue #4",
        "verified_on": "2026-10-24",
        "locked": True,
        "eligibility": "all",
    }
