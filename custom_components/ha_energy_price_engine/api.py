"""API v2: immutable verified final price ranges, with no I/O or calculation."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .const import API_VERSION, DOMAIN
from .models import utc


class Status(StrEnum):
    READY = "READY"
    INCOMPLETE = "INCOMPLETE"
    STALE = "STALE"
    ERROR = "ERROR"


class EngineNotReady(LookupError):
    """No producer is loaded; the consumer must wait, never substitute a price."""


@dataclass(frozen=True, slots=True)
class Site:
    site_id: str
    name: str
    timezone: str
    area: str


@dataclass(frozen=True, slots=True)
class Quote:
    start: datetime
    end: datetime
    price: float
    revision: int
    verified_at: datetime


@dataclass(frozen=True, slots=True)
class PriceWindow:
    site_id: str
    status: Status
    slots: tuple[Quote, ...]
    expected_slots: int
    available_slots: int
    revision: int
    verified_at: datetime | None
    reason: str | None
    currency: str = "DKK"
    unit: str = "DKK/kWh"
    vat_included: bool = True


def _quote(record):
    verified = utc(datetime.fromisoformat(json.loads(record.source_json)["verified_at"]))
    return Quote(record.start, record.end, record.final_price_incl_vat, record.revision, verified)


class PriceAPI:
    """Consumers receive slots only when the ENTIRE requested range is ready."""

    version = API_VERSION

    def __init__(self, hass):
        self.hass = hass

    def sites(self):
        return tuple(
            Site(c.site["id"], c.site["name"], c.site["timezone"], c.site["area"])
            for c in self.hass.data.get(DOMAIN, {}).values()
        )

    def _site(self, site_id):
        return next(
            (c for c in self.hass.data.get(DOMAIN, {}).values() if c.site["id"] == site_id), None
        )

    def lookup(self, site_id, start, end, *, now=None):
        """Half-open aligned UTC range. Historical quotes are for cost estimates.

        Current/future slots additionally require recent provider verification and
        the latest successful configuration's per-interval verification mask.
        Consumers must plan only future slots and accept only READY windows.
        """
        start, end, now = utc(start), utc(end), utc(now or dt_util.utcnow())
        if end <= start or start.timestamp() % 900 or end.timestamp() % 900:
            raise ValueError("Expected positive aware quarter-aligned range")
        c = self._site(site_id)
        if c is None:
            raise EngineNotReady("Selected price site is not loaded")
        rows = c.price_engine.lookup(site_id, start, end)
        expected = int((end - start).total_seconds() / 900)
        complete = (
            len(rows) == expected
            and rows[0].start == start
            and rows[-1].end == end
            and all(a.end == b.start for a, b in zip(rows, rows[1:]))
        )
        state = Status.READY if complete else Status.INCOMPLETE
        reason = None if complete else "Verified quarters are missing from the requested range"
        verified = []
        usable = {r.start for r in rows}
        if site_id in c.price_engine.load_errors:
            state, reason = Status.ERROR, c.price_engine.load_errors[site_id]
        elif end > now:
            if not c.settings_current:
                state, reason = Status.STALE, "Settings changed; waiting for verification"
                usable = {r.start for r in rows if r.end <= now}
            first = max(start, now).astimezone(ZoneInfo(c.site["timezone"])).date()
            last = (end - timedelta(microseconds=1)).astimezone(ZoneInfo(c.site["timezone"])).date()
            day = first
            while day <= last:
                report = c.schedule.days.get(site_id, {}).get(str(day), {})
                fresh = True
                try:
                    stamp = utc(datetime.fromisoformat(report["last_success"]))
                    if not 0 <= (now - stamp).total_seconds() <= 86400:
                        raise ValueError("Expired or future source verification")
                    verified.append(stamp)
                except ValueError, TypeError, KeyError:
                    fresh = False
                    if report.get("status") == "ERROR":
                        state, reason = Status.ERROR, report.get("reason")
                    elif state != Status.ERROR:
                        state, reason = (
                            Status.STALE if rows else Status.INCOMPLETE,
                            report.get("reason") or "Source verification is unavailable",
                        )
                if report.get("status") in {"ERROR", "STALE"}:
                    if report["status"] == "ERROR" or state != Status.ERROR:
                        state = Status.ERROR if report["status"] == "ERROR" else Status.STALE
                        reason = report.get("reason")
                allowed = set(report.get("verified_starts", []))
                for r in rows:
                    if (
                        r.end > now
                        and r.start.astimezone(ZoneInfo(c.site["timezone"])).date() == day
                        and (
                            not fresh
                            or r.start.isoformat() not in allowed
                            or report.get("status") in {"ERROR", "STALE"}
                        )
                    ):
                        usable.discard(r.start)
                if any(
                    r.end > now
                    and r.start.astimezone(ZoneInfo(c.site["timezone"])).date() == day
                    and r.start.isoformat() not in allowed
                    for r in rows
                ):
                    if state == Status.READY:
                        state, reason = (
                            Status.INCOMPLETE,
                            "A requested interval lacks verification under the current settings",
                        )
                day += timedelta(days=1)
        slots = ()
        if state == Status.READY:
            try:
                slots = tuple(_quote(r) for r in rows)
                if any(q.verified_at > now for q in slots):
                    raise ValueError("Stored source verification is in the future")
            except ValueError, TypeError, KeyError:
                state, reason = Status.ERROR, "Stored source verification is invalid"
                slots = ()
        return PriceWindow(
            site_id,
            state,
            slots,
            expected,
            len(usable) if state != Status.ERROR else 0,
            c.price_engine.revisions.get(site_id, 0),
            min(verified) if verified else min((q.verified_at for q in slots), default=None),
            reason,
        )

    def revision(self, site_id, start, revision):
        """Exact immutable quote used by a consumer; never substitute a newer price."""
        start = utc(start)
        if type(revision) is not int or revision < 1 or start.timestamp() % 900:
            raise ValueError("Expected aligned start and positive revision")
        c = self._site(site_id)
        if c is None:
            raise EngineNotReady("Selected price site is not loaded")
        rows = c.price_engine.lookup(site_id, start, start + timedelta(minutes=15))
        if site_id in c.price_engine.load_errors:
            raise EngineNotReady("Selected price history requires recovery")
        if rows and rows[0].revision == revision:
            return _quote(rows[0])
        for item in reversed(c.price_engine.audit.get(site_id, ())):
            for key in ("old", "new"):
                row = item[key]
                if row["revision"] == revision and datetime.fromisoformat(row["start"]) == start:
                    return Quote(
                        start,
                        datetime.fromisoformat(row["end"]),
                        row["final_price_incl_vat"],
                        revision,
                        utc(datetime.fromisoformat(json.loads(row["source_json"])["verified_at"])),
                    )
        return None


def get_api(hass, version=2):
    if type(version) is not int or version != API_VERSION:
        raise ValueError("This breaking MVP supports Price Engine API v2 only")
    if not hass.data.get(DOMAIN):
        raise EngineNotReady("Energy Price Engine is not loaded")
    return PriceAPI(hass)
