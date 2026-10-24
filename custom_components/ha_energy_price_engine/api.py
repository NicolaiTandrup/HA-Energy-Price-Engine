"""Versioned read-only consumer contract. No network or composition on reads."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from .const import API_VERSION, DOMAIN
from .models import utc
from .price_engine import PriceRecord


class Status(StrEnum):
    READY = "READY"
    INCOMPLETE = "INCOMPLETE"
    STALE = "STALE"
    ERROR = "ERROR"
    NOT_LOADED = "NOT_LOADED"


class EngineNotReady(LookupError):
    """Engine is not loaded; consumer must back off without treating this as free."""


@dataclass(frozen=True)
class Site:
    site_id: str
    name: str
    timezone: str
    area: str


@dataclass(frozen=True)
class PriceResult:
    api_version: int
    site_id: str
    status: Status
    records: tuple[PriceRecord, ...]
    expected_slots: int
    valid_slots: int
    last_success: str | None
    reason: str | None
    revision: int


class ConsumerAPI:
    """An immutable snapshot per call; caller cannot mutate producer state."""

    version = API_VERSION

    def __init__(self, hass):
        self._hass = hass

    def sites(self) -> tuple[Site, ...]:
        return tuple(
            Site(c.site["id"], c.site["name"], c.site["timezone"], c.site["area"])
            for c in self._hass.data.get(DOMAIN, {}).values()
        )

    def lookup(self, site_id: str, start: datetime, end: datetime, *, now=None) -> PriceResult:
        """Half-open UTC range on quarter boundaries; historical reads are supported."""
        from homeassistant.util import dt as dt_util

        start, end = utc(start), utc(end)
        now = utc(now or dt_util.utcnow())
        if end <= start or start.timestamp() % 900 or end.timestamp() % 900:
            raise ValueError("Expected positive, quarter-aligned aware range")
        c = next(
            (c for c in self._hass.data.get(DOMAIN, {}).values() if c.site["id"] == site_id), None
        )
        expected = int((end - start).total_seconds() / 900)
        if c is None:
            return PriceResult(
                1,
                site_id,
                Status.NOT_LOADED,
                (),
                expected,
                0,
                None,
                "Site integration is not loaded",
                0,
            )
        rows = c.price_engine.lookup(site_id, start, end)
        complete = (
            len(rows) == expected
            and rows[0].start == start
            and rows[-1].end == end
            and all(a.end == b.start for a, b in zip(rows, rows[1:]))
        )
        status = Status.READY if complete else Status.INCOMPLETE
        reports = []
        from zoneinfo import ZoneInfo

        zone = ZoneInfo(c.site["timezone"])
        first, last = (
            start.astimezone(zone).date(),
            (end - timedelta(microseconds=1)).astimezone(zone).date(),
        )
        day = first
        while day <= last:
            report = c.schedule.days.get(site_id, {}).get(str(day), {})
            reports.append(report)
            day += timedelta(days=1)
        reason = None
        successes = [r["last_success"] for r in reports if r.get("last_success")]
        # Operational errors matter for current/future reads; historical settlement
        # remains authoritative even if today's upstream is offline.
        if end > now:
            states = {r.get("status") for r in reports}
            if "ERROR" in states:
                status = Status.ERROR
            elif "STALE" in states:
                status = Status.STALE
            elif "INCOMPLETE" in states:
                status = Status.INCOMPLETE
            elif not reports or any(not r.get("last_success") for r in reports):
                status = Status.STALE if complete else Status.INCOMPLETE
            elif any(
                (now - datetime.fromisoformat(r["last_success"])).total_seconds() > 86400
                for r in reports
            ):
                status = Status.STALE
            reason = next((r.get("reason") for r in reports if r.get("reason")), None)
        if site_id in c.price_engine.load_errors:
            status, reason = Status.ERROR, c.price_engine.load_errors[site_id]
        return PriceResult(
            1,
            site_id,
            status,
            rows,
            expected,
            len(rows),
            min(successes) if successes else None,
            reason,
            c.price_engine.revisions.get(site_id, 0),
        )


def get_api(hass, version=1) -> ConsumerAPI:
    """Discover after integration setup; never auto-load or fetch on consumer reads."""
    if version != API_VERSION:
        raise ValueError(f"Unsupported Price Engine API version: {version}")
    if not hass.data.get(DOMAIN):
        raise EngineNotReady("Energy Price Engine is not loaded")
    return ConsumerAPI(hass)
