# Read-only Python price API v2

Beta.10 removes v1. No compatibility shim, HTTP service, producer-entry alias or
consumer calculation is needed. PE alone fetches, verifies, calculates and stores
prices. Calls below are synchronous immutable memory-index reads; they do not fetch,
compose tariffs, access SQLite or write. `get_api(hass, version=1)` raises ValueError.

```python
from custom_components.ha_energy_price_engine.api import get_api, Status, EngineNotReady
api = get_api(hass, version=2)
# Site(site_id, name, timezone, area); select the actual site explicitly.
sites = api.sites()
window = api.lookup(site_id, start, end, now=now)
if window.status == Status.READY:
    for quote in window.slots:
        consume(quote.start, quote.end, quote.price, quote.revision, quote.verified_at)
```

`start`/`end` must be aware, UTC-quarter aligned, positive and half-open `[start,end)`.
Offsets are normalized to UTC; local days may have 92, 96, 100 quarters. Unknown or
unloaded sites raise EngineNotReady; malformed ranges raise ValueError.

| PriceWindow field | Meaning |
|---|---|
| site_id | Exact selected durable site identity |
| status | READY, INCOMPLETE, STALE or ERROR for the entire requested range |
| slots | Tuple of immutable Quote; **empty unless the whole range is READY** |
| expected_slots / available_slots | Requested quarters / usable verified quarters |
| revision | Current monotonically increasing site publication revision |
| verified_at | Minimum actual latest source verification across requested future days; historical-only range uses stored quote verification |
| reason | Explanation when not READY |
| currency / unit / vat_included | DKK / DKK/kWh / True |

Quote has `start,end,price,revision,verified_at`. `price` is the finite full-precision
final marginal amount including VAT exactly once; negatives are valid. Quote
`verified_at` records the source verification used to create that immutable record.
It can predate a later successful unchanged source recheck, represented by window
`verified_at`. Units belong to the window. Quote exposes no private contract JSON.

Future/current coverage requires: exact contiguous rows; current loaded settings;
latest per-interval verification masks; actual provider success no older than 24 hours
and not future-dated; no source/grid/storage error or stale provider state. A missing
contract affects the actual intervals where it is absent. Complete future windows
can be READY even when earlier today is unknown. Missing tomorrow does not invalidate
a separately requested complete today range. NonREADY returns no optimization slots.

Historical-only ranges use immutable records for variable-cost estimates and do not
require today's provider to be healthy. Never use historical READY as permission to
plan future intervals. Consumers request future planning ranges beginning at the
next complete quarter; historical/session costing is separate. PE never allocates
energy or commands charging. `charging_cost.estimate_charging_cost` optionally costs
caller-supplied consecutive measured/planned kWh using these quotes, preserving
negative costs and missing-price unavailability.

`api.revision(site_id,start,revision)` returns exactly the current or retained old
Quote, or None. It never substitutes a newer amount. Save site/start/revision with
consumer cost references. Corrupt history fails closed and requires explicit recovery.

Subscribe to `ha_energy_price_engine_price_revision_v2`: payload is `api_version:2`,
`site_id`, `revision`, `affected_slots` (UTC starts), `start`,`end`. It is an
invalidation hint, emitted for actual changed future records, not verification-only
checks. Re-read the exact range; validate loaded sites again after unload/reload.
Events do not turn a nonREADY range into READY and are never charging commands.

Contract regressions use real HA producer/source/SQLite runtimes, independent-site
isolation, revisions, unload, unavailable ranges, no-I/O guards, DST and variable-cost
consumption. Old CM v1 is intentionally incompatible; see [CM handoff](INTEROPERABILITY.md).
