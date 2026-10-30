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


## Optional read-only charging-cost helper (beta.6)

API v1 and canonical DKK/kWh values are unchanged. `charging_cost.estimate_charging_cost`
accepts `get_api(hass)`, a site ID, consecutive `(aware_quarter_start, kwh_decimal)`
allocations and `energy_kind="planned"` or`"measured"`. Optional `producer_entry_id`
scopes the selected entry. CM/caller owns energy measurement/allocation and planning;
this helper never creates a plan, sends commands or persists an energy/cost ledger.
Future energy cannot be labelled measured. Explicit zero kWh is accepted; absent,
gapped,negative or nonfinite energy is rejected. Both decimal separators work.

All requested prices must be API READY; otherwise `estimated_cost_dkk` is null with
the unchanged price status/reason. Provisional visual prices are never substituted.
Successful output identifies planned/measured energy and each original price revision,
uses decimal weighted addition without per-quarter rounding, and explicitly marks
`fixed_subscriptions_included=false` and`is_settled_accounting=false`. It is a session
cost estimate using supplied energy, not settlement or household invoice reconstruction.
Native access: Final prices → Diagnostics → Charging cost estimate.


## Beta.7 readiness and presentation

API v1 and PriceRecord remain canonical technical DKK/kWh, with full numeric precision.
Preferred presentation is separate:øre/kWh2 decimals, optional DKK/kWh4. Consumers
must use stored API values, not rounded display entities, when computing energy cost.

`lookup(site_id,start,end,producer_entry_id=...)` checks exactly the half-open UTC
quarter-aligned range. A complete verified future window can be READY while a
full-day query is INCOMPLETE because pre-activation history is absent. Do not gate a
charging horizon on historical full-day coverage. Missing future quarters, stale/
failed verification and unconfirmed components remain fail-closed. UI window checks
use this same unchanged API and create no charging plan or consumer configuration.

Canonical records include normalized original spot in
`components_json.components.spot.ex_vat` (official Nord Pool); `incl_vat` retains its
VAT-inclusive counterpart. `source_json.input_unit/input_vat/verified_at` preserve
input/verification conventions. Full provider HTTP responses are not persisted.
The unchanged SQLite primary-key index and startup-loaded bisect memory index serve
stored values. Consumer reads do not connect to SQLite, fetch providers or compose.
Repeated-read, cold-reload, source-revision and 92/96/100-quarter tests are in
`tests/test_beta7_readiness.py`. Fixed subscriptions remain excluded.


## Beta.8 frontend transport (separate from CM APIv1)

The bundled Lovelace card uses the authenticated read-only HA WebSocket command
`ha_energy_price_engine/price_schedule` with one loaded PE `entity_id`. It checks
that user's HA entity read permission and returns at most today/tomorrow's quarters,
explicit null gaps, applied component/source snapshots, UTC/local-offset identities,
record revisions, today's DSO ranges and readiness. Arbitrary date/export parameters
are rejected. This adds no HA write service or charging control. It creates no large
Recorder attributes and does no provider/SQL/tariff recomposition on reads.
`schema_version:1` is the presentation response, not a new canonical consumer API.
Dashboard numbers are unrounded ore/kWh, formatted with2decimals by the card.
CM retains the unchanged full-precision DKK/kWh `get_api(hass,version=1)` contract.
See [dashboard installation/semantics](PRICE_DASHBOARD.md).
