"""Official built-in Nord Pool discovery, normalization and cached read service."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError

from .models import PriceSlot, validate_slots


def parse_prices(rows, *, multiplier=0.001):
    if not isinstance(rows, list):
        raise ValueError("Expected official Nord Pool quarter rows")
    parsed = []
    for row in rows:
        if isinstance(row["price"], bool):
            raise ValueError("Boolean prices are invalid")
        parsed.append(
            PriceSlot(
                datetime.fromisoformat(row["start"]),
                datetime.fromisoformat(row["end"]),
                float(row["price"]) * multiplier,
            )
        )
    return validate_slots(parsed)


async def ensure_official_nordpool(hass):
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
    entries = [e for e in hass.config_entries.async_entries("nordpool") if e.disabled_by is None]
    if len(entries) != 1:
        return {}
    entry = entries[0]
    result = {"nordpool_entry": entry.entry_id}
    areas = entry.options.get("areas", entry.data.get("areas", []))
    if len(areas) == 1 and areas[0] in {"DK1", "DK2"}:
        result["area"] = areas[0]
    return result


class OfficialPrices:
    def __init__(self, hass):
        self.hass, self.cache = hass, {}
        self.attempts = {}
        self.invalidated = set()
        self.errors = set()

    async def get(self, site, now, *, force=False, dates=None):
        await ensure_official_nordpool(self.hass)
        selected = self.hass.config_entries.async_get_entry(site["nordpool_entry"])
        if selected is None or selected.state != ConfigEntryState.LOADED:
            raise HomeAssistantError(
                "Official Nord Pool entry is not loaded; waiting for provider recovery"
            )
        rows = []
        self.last_errors = []
        today = now.astimezone(ZoneInfo(site["timezone"])).date()
        for day in dates or (today, today + timedelta(days=1)):
            key = (site["nordpool_entry"], site.get("area", "DK2"), str(day))
            cached = self.cache.get(key)
            attempted = self.attempts.get(key)
            if (
                force
                or key in self.invalidated
                or cached is None
                or (now - cached[0]).total_seconds() >= 3600
            ) and (force or attempted is None or (now - attempted).total_seconds() >= 900):
                self.attempts[key] = now
                try:
                    response = await self.hass.services.async_call(
                        "nordpool",
                        "get_prices_for_date",
                        {
                            "config_entry": key[0],
                            "date": key[2],
                            "areas": [key[1]],
                            "currency": "DKK",
                        },
                        blocking=True,
                        return_response=True,
                    )
                    data = response[key[1]]
                    parsed = parse_prices(data)
                    if len(parsed) != len(data):
                        raise ValueError(
                            "Official Nord Pool requires explicit 15-minute resolution"
                        )
                    self.cache[key] = (now, data)
                    self.invalidated.discard(key)
                    self.errors.discard(key)
                except HomeAssistantError, ValueError, KeyError, TypeError, TimeoutError:
                    self.errors.add(key)
                    self.last_errors.append(str(day))
                    # Cached values expire rather than hiding a broken price source.
                    if cached is None or (now - cached[0]).total_seconds() >= 7200:
                        continue
            if key in self.errors and str(day) not in self.last_errors:
                self.last_errors.append(str(day))
            cached = self.cache.get(key)
            if cached and (now - cached[0]).total_seconds() < 7200:
                rows.extend(cached[1])
        self.cache = {k: v for k, v in self.cache.items() if (now - v[0]).total_seconds() < 172800}
        self.attempts = {
            k: v for k, v in self.attempts.items() if (now - v).total_seconds() < 172800
        }
        slots = parse_prices(rows)
        return slots
