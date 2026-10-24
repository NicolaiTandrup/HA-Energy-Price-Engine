"""Atomic precomputed price storage. Readers never fetch or compose prices."""

import json
from asyncio import Lock
from bisect import bisect_left
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from hashlib import sha256
from math import isfinite
from zoneinfo import ZoneInfo

from homeassistant.helpers.storage import Store

from .models import PriceSlot, utc
from .price_components import compose_dated
from .prices import all_in


def source_identity(value):
    if isinstance(value, dict):
        return {
            k: source_identity(v)
            for k, v in value.items()
            if k not in {"verified_at", "fetched_at", "warning"}
        }
    if isinstance(value, list):
        return [source_identity(v) for v in value]
    return value


def day_bounds(day: date, timezone="Europe/Copenhagen"):
    zone = ZoneInfo(timezone)
    return (
        datetime.combine(day, time(), zone).astimezone(UTC),
        datetime.combine(day + timedelta(days=1), time(), zone).astimezone(UTC),
    )


@dataclass(frozen=True)
class PriceRecord:
    site_id: str
    start: datetime
    end: datetime
    final_price_incl_vat: float
    components_json: str
    source_json: str
    calculated_at: datetime
    revision: int
    currency: str = "DKK"
    unit: str = "DKK/kWh"


def calculate(site_id, slots, tariff, source, now, revision):
    """Update-time composition; store explicit component/VAT conventions."""
    priced = all_in(slots, tariff) if "components" not in tariff else slots
    result = []
    for raw, final in zip(slots, priced, strict=True):
        if "components" in tariff:
            final_value, components = compose_dated(raw, tariff)
            final = PriceSlot(raw.start, raw.end, final_value)
        elif tariff.get("mode", "all_in") == "all_in":
            components = {"external_all_in": raw.price, "amounts_include_vat": True}
        else:
            grid = sum(
                g.price
                for g in tariff.get("grid_slots", [])
                if g.start <= raw.start and g.end >= raw.end
            )
            ex = {
                "spot": raw.price / (1 + tariff.get("vat", 0))
                if tariff.get("mode") == "spot_incl_vat"
                else raw.price,
                "dso": tariff.get("grid", 0) + grid,
                "tax": tariff.get("tax", 0),
                "supplier": tariff.get("supplier", 0),
            }
            components = {
                "ex_vat": ex,
                "vat_rate": tariff.get("vat", 0),
                "vat": final.price - sum(ex.values()),
                "amounts_include_vat": False,
            }
        result.append(
            PriceRecord(
                site_id,
                utc(raw.start),
                utc(raw.end),
                final.price,
                json.dumps(components, sort_keys=True),
                json.dumps(source, sort_keys=True),
                now,
                revision,
            )
        )
    return tuple(result)


def validate_records(records, site):
    previous = None
    for record in records:
        if (
            record.site_id != site
            or record.currency != "DKK"
            or record.unit != "DKK/kWh"
            or record.start.tzinfo is None
            or record.end.tzinfo is None
            or record.end - record.start != timedelta(minutes=15)
            or record.start.timestamp() % 900 != 0
            or isinstance(record.final_price_incl_vat, bool)
            or not isfinite(record.final_price_incl_vat)
            or type(record.revision) is not int
            or record.revision < 1
            or record.calculated_at.tzinfo is None
            or (previous is not None and record.start < previous)
        ):
            raise ValueError("Invalid/duplicate price interval, unit or site")
        if not isinstance(json.loads(record.components_json), dict) or not isinstance(
            json.loads(record.source_json), dict
        ):
            raise ValueError("Price provenance must be a JSON object")
        previous = record.end


class PriceEngine:
    """Per-site HA Store snapshots, serialized writes and immutable lookup results.

    Already-started intervals retain their original amounts/provenance. Corrections
    replace future records only; history is retained permanently by default. Disk save succeeds
    before the memory index changes, so failed writes leave old reads authoritative.
    """

    def __init__(self, hass, entry_id, retention_days=None):
        self.hass, self.entry_id = hass, entry_id
        self.retention_days = retention_days
        self.records, self.index, self.planning, self.signatures, self.revisions = (
            {},
            {},
            {},
            {},
            {},
        )
        self.price_keys = {}
        self.batch_signatures = {}
        self.audit = {}
        self.load_errors = {}
        self.lock = Lock()

    def store(self, site):
        return Store(self.hass, 1, f"ha_energy_price_engine.{self.entry_id}.{site}.prices")

    def _install(self, site, records, signature, revision):
        self.records[site] = tuple(records)
        self.index[site] = tuple(r.start for r in records)
        self.planning[site] = tuple(
            PriceSlot(r.start, r.end, r.final_price_incl_vat) for r in records
        )
        self.signatures[site], self.revisions[site] = signature, revision
        self.price_keys[site] = sha256(
            str(tuple((r.start, r.end, r.final_price_incl_vat) for r in records)).encode()
        ).hexdigest()

    async def async_load(self, sites):
        for site in sites:
            saved = await self.store(site).async_load()
            if not saved:
                continue
            try:
                records = []
                for row in saved["records"]:
                    item = dict(row)
                    for key in ("start", "end", "calculated_at"):
                        item[key] = datetime.fromisoformat(item[key])
                    records.append(PriceRecord(**item))
                validate_records(records, site)
                self._install(site, records, saved["signature"], saved["revision"])
                self.batch_signatures[site] = saved.get("batch_signatures", {})
                self.audit[site] = saved.get("audit", [])
            except ValueError, TypeError, KeyError:
                # Corrupt caches cannot create plausible zero/partial price tables.
                self._install(site, (), "", 0)
                self.load_errors[site] = "Invalid persisted price ledger"

    async def async_update(self, site, slots, tariff, source, now):
        slots = tuple(slots)
        if not slots:
            return False
        now = utc(now)
        if "components" in tariff:
            dates = {
                str(
                    s.start.astimezone(ZoneInfo(tariff.get("timezone", "Europe/Copenhagen"))).date()
                )
                for s in slots
            }
            tariff = {
                **tariff,
                "components": [
                    r
                    for r in tariff["components"]
                    if any(r["valid_from"] <= day < r["valid_to"] for day in dates)
                ],
            }
        payload = {
            "slots": [asdict(s) for s in slots],
            "tariff": tariff,
            "source": source_identity(source),
        }
        signature = sha256(json.dumps(payload, default=str, sort_keys=True).encode()).hexdigest()
        batch_key = f"{slots[0].start.isoformat()}/{slots[-1].end.isoformat()}"
        async with self.lock:
            if self.batch_signatures.get(site, {}).get(batch_key) == signature:
                return False
            revision = self.revisions.get(site, 0) + 1
            old = {r.start: r for r in self.records.get(site, ())}
            # A tariff edit must not even attempt to reprice settled intervals.
            eligible = tuple(s for s in slots if s.start >= now or s.start not in old)
            candidates = calculate(site, eligible, tariff, source, now, revision)
            validate_records(candidates, site)
            return await self._apply(site, candidates, signature, batch_key, now)

    async def _apply(self, site, candidates, signature, batch_key, now):
        old = {r.start: r for r in self.records.get(site, ())}
        revision = self.revisions.get(site, 0) + 1
        audit = list(self.audit.get(site, []))
        for record in candidates:
            prior = old.get(record.start)
            if prior and (
                record.start < now
                or (
                    prior.final_price_incl_vat == record.final_price_incl_vat
                    and prior.components_json == record.components_json
                    and source_identity(json.loads(prior.source_json))
                    == source_identity(json.loads(record.source_json))
                )
            ):
                continue
            if prior:
                audit.append(
                    {
                        "changed_at": now.isoformat(),
                        "old": self._serialize(prior),
                        "new": self._serialize(record),
                    }
                )
            old[record.start] = record
        records = tuple(
            r
            for _, r in sorted(old.items())
            if self.retention_days is None or r.end > now - timedelta(days=self.retention_days)
        )
        validate_records(records, site)
        if records == self.records.get(site, ()):
            self.signatures[site] = signature
            self.batch_signatures.setdefault(site, {})[batch_key] = signature
            return False
        signatures = {**self.batch_signatures.get(site, {}), batch_key: signature}
        await self.store(site).async_save(
            {
                "records": [self._serialize(r) for r in records],
                "signature": signature,
                "revision": revision,
                "batch_signatures": signatures,
                "audit": audit,
            }
        )
        self._install(site, records, signature, revision)
        self.batch_signatures[site], self.audit[site] = signatures, audit
        self.load_errors.pop(site, None)
        return True

    async def async_reconfigure(self, site, tariff_builder, now):
        """Recompose only selected future rows; atomic across affected periods.

        tariff_builder is a write-side selector returning None for unaffected
        rows. Existing stored raw spot/source provenance is reused without HTTP.
        """
        now = utc(now)
        async with self.lock:
            candidates = []
            for row in self.records.get(site, ()):
                if row.start < now:
                    continue
                tariff = tariff_builder(row)
                if tariff is None:
                    continue
                components = json.loads(row.components_json)["components"]
                raw = PriceSlot(row.start, row.end, components["spot"]["ex_vat"])
                candidates.extend(
                    calculate(
                        site,
                        [raw],
                        tariff,
                        json.loads(row.source_json),
                        now,
                        self.revisions.get(site, 0) + 1,
                    )
                )
            if not candidates:
                return False
            validate_records(candidates, site)
            signature = sha256(
                json.dumps([self._serialize(r) for r in candidates], sort_keys=True).encode()
            ).hexdigest()
            return await self._apply(site, tuple(candidates), signature, "configuration", now)

    @staticmethod
    def _serialize(record):
        row = asdict(record)
        for key in ("start", "end", "calculated_at"):
            row[key] = row[key].isoformat()
        return row

    def lookup(self, site, start, end):
        keys = self.index.get(site, ())
        a = max(0, bisect_left(keys, start) - 1)
        b = bisect_left(keys, end)
        return tuple(r for r in self.records.get(site, ())[a:b] if r.end > start)

    def slots(self, site, start=None, end=None):
        if start is None:
            return self.planning.get(site, ())
        keys = self.index.get(site, ())
        a = max(0, bisect_left(keys, start) - 1)
        b = bisect_left(keys, end) if end else len(keys)
        return tuple(s for s in self.planning.get(site, ())[a:b] if s.end > start)

    def complete_day(self, site, day, timezone="Europe/Copenhagen"):
        start, end = day_bounds(day, timezone)
        rows = self.lookup(site, start, end)
        return (
            bool(rows)
            and rows[0].start == start
            and rows[-1].end == end
            and all(a.end == b.start for a, b in zip(rows, rows[1:]))
        )
