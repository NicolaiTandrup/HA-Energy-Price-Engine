# Unreleased EV Charge Manager handoff — API v2

**CM has not been changed or declared compatible by this PE mission.** Its existing
v1 adapter must be updated before pairing with PE beta.10. The owner explicitly
allows this break; do not retain a v1 producer shim merely to pass earlier consumer
suites. Immutable historical CM references were inspected, not edited. No CM controls
or live HA were accessed. These are concrete required source changes for CM review.

Inspected reference: CM PR26 `5ef7115a9599e1ff25019e91b3737500853b9a38`,
`custom_components/ev_charge_manager/price_consumer.py` and associated tests. PE's
original tariff implementation attribution remains [here](PROVENANCE.md).

1. Replace `get_api(hass,version=1)` with version2. Discover `api.sites()` and persist
   the selected PE `site_id`. Remove the redundant producer-entry ID from new CM
   setup/Options and price mapping. Do not infer identity from names or entity IDs.
   Existing development CM mappings need explicit reselection after PE site reset.
2. Replace `result.records` with `result.slots`, `record.final_price_incl_vat` with
   `quote.price`, `valid_slots` with `available_slots`, and `last_success` with the
   aware datetime `verified_at`. API version is `api.version == 2`; window units are
   explicit DKK/kWh including VAT. Site/unit fields no longer repeat on every quote.
3. Remove v1 normalization to dictionaries and its `decode` scaffolding. Require
   exact selected `window.site_id`, READY, DKK/DKK/kWh/True, expected count == available
   count == quote count, aware aligned contiguous slots matching `[start,end)`, finite
   nonboolean prices, positive per-quote revisions and nonfuture verification. On
   EngineNotReady, ValueError, unsupported version, STALE/ERROR/INCOMPLETE, withhold that
   planning range and show the reason. Do not use retained rows or replace gaps with0.
4. Separate the future optimizer window (next complete quarter onwards) from historical
   energy/cost queries. The old `(now-3minutes)` start can include unavailable first-
   activation current quarters. Split today/tomorrow at actual local midnight; accept
   only each complete READY requested subrange. Missing tomorrow must not invalidate
   independently complete today's future planning. Do not reconstruct tariffs in CM.
5. Subscribe to `ha_energy_price_engine_price_revision_v2`, filter exactsite and invalidate
   affected future ranges. Validate site presence with `api.sites()` after unload or
   reset. Remove direct PE entry/runtime introspection. New site IDs require reselection.
6. Keep measured-energy allocation/history/journal/control safeguards in CM. Save
   `(site_id,quarter_start,quote.revision,quote.price)` for session references; use
   `api.revision` for exact historical corrections. Historical quotes retain their
   original source verification, while window verification reflects fresh unchanged
   provider checks. Do not enforce today's source freshness on immutable historical
   costing; enforce freshness/readiness for future optimization.
7. Update CM `tests/test_price_consumer.py`, setup/Options tests and coupled-runtime
   cases around actual PE API2. Cover first activation, multiple sites, missing/future
   rates, stale/future source timestamps, actual revisions, restart/unload, negative
   costs, both DST changes and producer errors. Run CM's full suite separately. PE
   `tests/test_integration.py` and `test_statistics_and_cost.py` establish the new
   producer contract, not cross-repository compatibility with unchanged CM code.

Minimal future consumption (no fees/VAT/source calls in CM):

```python
api = get_api(hass, version=2)
result = api.lookup(selected_site_id, next_quarter, deadline)
if result.status != Status.READY:
    return unavailable(result.reason)
assert (result.currency, result.unit, result.vat_included) == ("DKK", "DKK/kWh", True)
return tuple(PriceSlot(q.start, q.end, q.price) for q in result.slots)
```

PE publication does not authorize enabling CM charging controls. A future CM adapter
PR, its complete CI and owner development acceptance are separate work.
