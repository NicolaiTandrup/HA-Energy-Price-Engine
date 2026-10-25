"""Explicit source catalog and provider-neutral timestamped entity contract."""

from datetime import datetime

from .models import utc

UNIT_MULTIPLIERS = {"DKK/kWh": 1.0, "DKK/MWh": 0.001, "ore/kWh": 0.01}
BASES = ("spot_ex_vat", "spot_incl_vat", "all_in")


def source_defaults(hass):
    """Suggest one unambiguous official entry, never a contract or another site.

    Defaults still need explicit user submission. Multiple entries or price areas
    require a choice; titles/entity suffixes never establish ownership.
    """
    entries = [e for e in hass.config_entries.async_entries("nordpool") if e.disabled_by is None]
    if len(entries) != 1:
        return {}
    entry = entries[0]
    result = {"nordpool_entry": entry.entry_id}
    areas = entry.options.get("areas", entry.data.get("areas", []))
    if isinstance(areas, list) and len(areas) == 1:
        result["area"] = areas[0]
    return result


def validate_entity_source(state, site, now):
    """Require explicit money/VAT and provider verification, not HA report time."""
    attributes = state.attributes
    if attributes.get("currency") != "DKK":
        raise ValueError("Entity source must explicitly declare DKK currency")
    if attributes.get("unit_of_measurement") != site["price_unit"]:
        raise ValueError("Entity source unit differs from the confirmed source unit")
    included = site["price_basis"] in {"spot_incl_vat", "all_in"}
    if type(attributes.get("vat_included")) is not bool or attributes["vat_included"] != included:
        raise ValueError("Entity source VAT convention differs from the confirmed price basis")
    verified = utc(datetime.fromisoformat(attributes["verified_at"]))
    if not 0 <= (now - verified).total_seconds() <= site.get("stale_minutes", 40) * 60:
        raise ValueError("Entity source verification is missing, stale or future-dated")
    return verified


async def ensure_official_nordpool(hass):
    """A legacy custom component can shadow the same domain; never mistake it for core."""
    from homeassistant.loader import async_get_integration

    integration = await async_get_integration(hass, "nordpool")
    if not integration.is_built_in:
        raise ValueError(
            "Official Home Assistant Nord Pool is required; a legacy custom component shadows this domain"
        )


async def async_source_defaults(hass):
    try:
        await ensure_official_nordpool(hass)
    except ValueError:
        return {}
    return source_defaults(hass)
