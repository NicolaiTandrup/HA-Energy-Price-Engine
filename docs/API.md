# Read-only consumer API v1

Discover after the integration is loaded:

```python
from custom_components.ha_energy_price_engine.api import EngineNotReady, Status, get_api
from custom_components.ha_energy_price_engine.const import PRICE_REVISION_EVENT

try:
    api = get_api(hass, version=1)
except EngineNotReady:
    # Defer planning, retain safe prior policy and retry with bounded backoff.
    return

sites = api.sites()  # immutable (site_id, name, timezone, area) descriptors
result = api.lookup(site_id, aware_start, aware_end)
if result.status != Status.READY or result.valid_slots != result.expected_slots:
    return  # Never substitute zero or recompute prices in the consumer.
# Final VAT-inclusive DKK/kWh values, already calculated and durably committed.
slots = result.records
```

Ranges are half-open `[start, end)`, timezone-aware and quarter-hour aligned.
Use UTC instants when selecting slots; local day bounds handle 92/96/100-slot DST
days. Invalid ranges and unsupported versions raise ValueError. No loaded producer
raises EngineNotReady at discovery; a retained API handle returns NOT_LOADED for a
site unloaded later. Another site's failure never substitutes its prices.

`PriceResult` is frozen: API version, site ID, status, tuple of frozen `PriceRecord`,
expected/valid counts, last source success, reason and current site revision.
Records include UTC start/end, final_price_incl_vat, currency DKK, unit DKK/kWh,
components_json and source_json (fresh decoded JSON cannot mutate the producer),
calculated_at and record revision. Older immutable records may retain an older
revision after a future-only correction. Components carry normalized ex-VAT,
VAT and gross amounts plus source/effective/verification/lock metadata. Fixed
subscriptions are explicit and excluded from marginal totals.

Readiness: READY means coverage and current operational verification; INCOMPLETE
means missing/rejected intervals; STALE means retained data with expired verification
or degraded cached source; ERROR means source/storage verification failed;
NOT_LOADED means the configured site is absent. Complete historic settled ranges
remain readable during a current source outage. Future/current queries consider
all requested dates' operational state and verification age. Returned old rows are
not evidence of READY. Source timestamps and calculated_at have different meanings.

Subscribe with `hass.bus.async_listen(PRICE_REVISION_EVENT, callback)`. The literal
event is `ha_energy_price_engine_price_revision_v1`; data includes api_version,
site_id, revision, start/end and affected_slots (UTC ISO start timestamps). Emitted
only after successful durable writes when final amounts for unstarted slots actually
changed or first became known. Metadata-only verification does not emit. Re-query
the affected range; event payloads do not carry mutable price tables. Subscription
does not imply readiness; a consumer should also retry discovery with bounded
backoff and react to HA config entry load/unload. Events do not change optimizer
cadence. Preserve the EV Manager's 30-minute cycle and earliest-slot tie-break.

No write service, tariff editor or price arithmetic is exposed to consumers. UI
options are the producer's business configuration boundary. The current price and
readiness sensors support dashboards; long range consumers use the batch API.
See INTEROPERABILITY.md for migration and remaining real-world parity work.

## Additive beta contract details

`Site` and `PriceResult` now also expose `producer_entry_id`. Existing v1 calls
remain valid; callers may pass `producer_entry_id=` to `lookup` for explicit entry
ownership verification. A mismatched entry returns NOT_LOADED with no prices.
Version requests require an actual supported integer; booleans are not versions.
Invalid, naive or future verification timestamps fail closed. Source verification
is the successful provider time, never the time of a cache read or UI refresh.

`serialize_result(result)` is an optional machine-readable view, not a new HA
service. Schema and synthetic 92/96/100-slot/partial snapshots are in
`docs/contracts/price-api-v1.*.json`. PR #6's former service proposal is superseded;
no `get_prices` service or second event name is introduced.

`lookup_revision(site_id, start, revision, producer_entry_id=...)` returns an exact
immutable published record from current data or the durable correction audit.
Missing/unloaded revisions return None; accounting must never substitute a different
revision or zero. Retrieval performs no HTTP, price calculation or storage writes.
Existing settled records remain untouched by automatic corrections.

Pinned actual CM #15 and #16 decoders consume the same machine-tested snapshots.
`tools/test_two_runtime.py` additionally starts actual PE+CM coordinators together
in a disposable HA harness, verifies future revisions after HA's bounded coordinator
debounce, duplicate-replan suppression, and invalid forecasts after producer unload.
All data and provider/device observations are synthetic; no real controls are called.
