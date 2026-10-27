"""Read-only onboarding verification using the real adapters and canonical calculator.

No draft can alter a site's ledger. Final Save starts normal transactional runtime.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .price_components import REQUIRED, active_hours, danish_public_components, eligible
from .price_engine import calculate, day_bounds
from .price_update import PriceUpdater


class PreviewEngine:
    """Minimal in-memory sink; canonical calculate(), never a second pricing formula."""

    entry_id = "onboarding-preview"

    def __init__(self, entry_id):
        self.entry_id = entry_id
        self.records = {}

    async def async_update(self, key, slots, tariff, source, now):
        self.records[key] = tuple(calculate(key, slots, tariff, source, now, 0))
        return False

    def complete_day(self, key, day, timezone):
        start, end = day_bounds(day, timezone)
        rows = [r for r in self.records.get(key, ()) if start <= r.start < end]
        return len(rows) == int((end - start).total_seconds() / 900)


def component_coverage(site, day):
    """Report every missing required period, including grid, not just the first failure."""
    if site.get("price_basis") == "all_in":
        return {}
    rules = list(site.get("dated_components", []))
    if site.get("danish_public_rates"):
        rules += danish_public_components()
    start, end = day_bounds(day, site["timezone"])
    expected_hours = set()
    while start < end:
        expected_hours.add(start.astimezone(ZoneInfo(site["timezone"])).hour)
        start += timedelta(minutes=15)
    result = {}
    for key in sorted(REQUIRED | {"dso"}):
        hours = set().union(
            *(
                active_hours(r)
                for r in rules
                if r["id"] == key
                and r["valid_from"] <= str(day) < r["valid_to"]
                and eligible(r, site, day)
            )
        )
        result[key] = expected_hours <= hours
    return result


async def verify_site(hass, site, entry_id="onboarding-preview"):
    """Read providers for both days, calculate if possible, return factual UI data."""
    engine = PreviewEngine(entry_id)
    updater = PriceUpdater(hass, engine)
    await updater.tariffs.load()
    now = dt_util.utcnow()
    today = now.astimezone(ZoneInfo(site["timezone"])).date()
    results = {}
    for day in (today, today + timedelta(days=1)):
        await updater.refresh(site, now, force=True, dates=[day])
        report = dict(updater.status[site["id"]])
        report["raw"] = updater.raw_reports.get(str(day), {})
        report["coverage"] = component_coverage(site, day)
        report["calculated_slots"] = (
            len(engine.records.get(site["id"], ())) if report["status"] == "READY" else 0
        )
        results[str(day)] = report
    return results
