"""Official product suggestions require fresh evidence and explicit private confirmation."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.ha_energy_price_engine.supplier_offers import get_offers, parse_offer


def page(name="Basis El", amount="16,5", monthly="0"):
    return f"<h1>{name}</h1><p>Du betaler den aktuelle elpris fra elbørsen Nord Pool plus et tillæg på {amount} øre/kWh.</p><p>Du betaler {monthly} kr. i abonnement</p>"


def test_unknown_vat_never_becomes_an_automatic_assumption():
    now = datetime(2026, 10, 27, 18, tzinfo=UTC)
    offer = parse_offer("ewii_basis", page(), "", now)
    assert offer["markup_ore"] == 16.5 and offer["monthly_dkk"] == 0
    assert offer["vat_included"] is None and offer["vat_source"] == "user_confirmation_required"
    offer = parse_offer("ewii_basis", page(), "Alle priser er inklusive moms", now)
    assert offer["vat_included"] is True
    with pytest.raises(ValueError):
        parse_offer("ewii_basis", page().replace("tillæg på", "unknown new layout"), "", now)


async def test_fresh_offers_expire_and_do_not_turn_into_permanent_presets(hass, freezer):
    freezer.move_to("2026-10-27T18:00:00Z")

    async def source(hass, url):
        if url.endswith("/basis-el/"):
            return page()
        if url.endswith("/plus-el/"):
            return "<h1>Plus El</h1>Du betaler den aktuelle elpris fra elbørsen Nord Pool, plus et tillæg på 6,5 øre/kWh. Derudover er der et månedligt abonnement på 29 kr."
        return ""

    with patch(
        "custom_components.ha_energy_price_engine.supplier_offers._fetch", side_effect=source
    ):
        offers = await get_offers(hass)
    assert offers["ewii_plus"]["monthly_dkk"] == 29 and offers["ewii_plus"]["vat_included"] is None
    freezer.move_to("2026-10-29T18:00:00Z")
    with patch(
        "custom_components.ha_energy_price_engine.supplier_offers._fetch",
        AsyncMock(side_effect=OSError("Offline")),
    ):
        assert await get_offers(hass) == {}
