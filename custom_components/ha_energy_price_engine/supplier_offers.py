"""Bounded public EWII suggestions, never proof of an individual customer's terms."""

import asyncio
import hashlib
import json
import re
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

URLS = {
    "ewii_basis": "https://www.ewii.dk/privat/el/basis-el/",
    "ewii_plus": "https://www.ewii.dk/privat/el/plus-el/",
}
VAT_URL = "https://www.ewii.dk/privat/el/elpriser/"


class PublicText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data.strip())


def text(html):
    parser = PublicText()
    parser.feed(html)
    return re.sub(r"\s+", " ", " ".join(parser.parts))


def parse_offer(key, html, vat_html, now):
    """Only the primary published spot supplement; no campaign guessing."""
    body = text(html)
    vat = text(vat_html)
    name = "Basis El" if key == "ewii_basis" else "Plus El"
    if name not in body:
        raise ValueError("Product identity missing")
    match = re.search(
        r"Du betaler den aktuelle elpris fra elbørsen Nord Pool,? plus et tillæg på (\d+(?:[,.]\d+)?) øre/kWh",
        body,
    )
    if not match:
        raise ValueError("Primary spot markup could not be verified")
    monthly = (
        re.search(r"månedligt abonnement på (\d+(?:[,.]\d+)?) kr", body)
        if key == "ewii_plus"
        else re.search(r"Du betaler (\d+(?:[,.]\d+)?) kr\. i abonnement", body)
    )
    if not monthly:
        raise ValueError("Monthly subscription could not be verified")
    vat_verified = bool(
        re.search(r"(?i)(?:alle|angivne|viste) priser.{0,40}(?:inklusive|inkl\.) moms", vat)
    )
    return {
        "name": "EWII " + name,
        "markup_ore": float(match[1].replace(",", ".")),
        "monthly_dkk": float(monthly[1].replace(",", ".")),
        "vat_included": True if vat_verified else None,
        "url": URLS[key],
        "vat_source": VAT_URL if vat_verified else "user_confirmation_required",
        "verified_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
        "html_sha256": hashlib.sha256(html.encode()).hexdigest(),
        "vat_html_sha256": hashlib.sha256(vat_html.encode()).hexdigest(),
        "public_offer_only": True,
    }


async def _fetch(hass, url):
    session = async_get_clientsession(hass)
    async with session.get(url, timeout=8, allow_redirects=False) as response:
        if response.status != 200 or urlsplit(str(response.url)).hostname != "www.ewii.dk":
            raise ValueError("Official product source unavailable")
        data = await response.content.read(1048577)
        if len(data) > 1048576:
            raise ValueError("Official product source too large")
        return data.decode("utf-8")


async def get_offers(hass):
    """Fetch fresh sources; use only an unexpired independently verified snapshot."""
    now = dt_util.utcnow()
    cache = hass.data.setdefault("ha_energy_price_engine_public_offers", {})
    if cache.get("checked") and (now - cache["checked"]).total_seconds() < 1800:
        return {
            k: v
            for k, v in cache["offers"].items()
            if dt_util.parse_datetime(v["expires_at"]) > now
        }
    offers = {}
    try:
        async with asyncio.timeout(10):
            responses = await asyncio.gather(
                _fetch(hass, VAT_URL),
                *(_fetch(hass, url) for url in URLS.values()),
                return_exceptions=True,
            )
            vat = responses[0] if isinstance(responses[0], str) else ""
            for (key, _), html in zip(URLS.items(), responses[1:], strict=True):
                if isinstance(html, str):
                    try:
                        offers[key] = parse_offer(key, html, vat, now)
                    except ValueError, TypeError:
                        continue
    except OSError, ValueError, TimeoutError:
        pass
    if not offers:

        def load():
            path = Path(__file__).parent / "data/supplier_offers.json"
            return json.loads(path.read_text()) if path.exists() else {}

        try:
            snapshot = await hass.async_add_executor_job(load)
            for key, offer in snapshot.get("offers", {}).items():
                fetched = dt_util.parse_datetime(offer.get("verified_at", ""))
                expires = dt_util.parse_datetime(offer.get("expires_at", ""))
                if (
                    key in URLS
                    and offer.get("url") == URLS[key]
                    and offer.get("vat_source") in {VAT_URL, "user_confirmation_required"}
                    and (
                        type(offer.get("vat_included")) is bool or offer.get("vat_included") is None
                    )
                    and fetched
                    and expires
                    and fetched <= now < expires
                    and (expires - fetched).total_seconds() <= 86400
                ):
                    offers[key] = offer
        except OSError, ValueError, KeyError, TypeError:
            pass
    cache.update(checked=now, offers=offers)
    return offers
