# Development handoff

Updated 2026-10-24. Read AGENTS.md first. This is the single permanent handoff.

## Branches, drafts and validated commits

- Producer: `feat/standalone-price-engine`, based on `981e489` (main).
  Draft https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/pull/7.
- Validated producer code: `e36e3e455b85a81fe2cf099a08ba4f6c8de37f49`.
  All SIX exact-head push/PR checks passed: tests, hassfest and HACS.
- Companion consumer: `feat/price-engine-consumer`, based on original EV PR #12.
  Draft https://github.com/NicolaiTandrup/HA-EV-Charge-Manager/pull/15 targets
  `feat/verified-danish-pricing`. Code `088c8fad00a0eb79fec246e35637d26655e1eb1c`:
  all SIX exact-head push/PR tests, hassfest and HACS passed.
- Current checkpoint subject: `docs: record validated producer and consumer handoff`.
  This handoff-only checkpoint does not change validated application code. Its own
  SHA cannot be recorded in this document; inspect Git/PR checks for the current head.
- Earlier checkpoints: workflow `e50d0df`, proven core `5eb20de`, native producer
  `3f7f684`, hardening `a5cf2c2`, metadata ordering `f362507`. All are pushed.

## Implemented preview for Issues #1–#5

- #1: native `ha_energy_price_engine`, independent per-site config entries,
  lifecycle, sensors, ADR-001, immutable read-only API v1, README, attribution,
  permanent workflow and CI. No vehicle/charging code belongs to this producer.
- #2: ported atomic HA Store ledger, indexed UTC range lookups, permanent history
  (upstream had 365-day retention), durable old/new future-correction audit,
  per-day signatures, failed-write protection and settled-history preservation.
  Reads perform no HTTP, calculation or persistence. Unknown prices are never zero.
- #3: Copenhagen 13:05 primary; 13:20/13:40 conditional retry; 23:59 conditional
  rescue; 00:01 unconditional current-day sync; startup catch-up; exact-day
  validation; READY/INCOMPLETE/STALE/ERROR diagnostics; source debounce/backoff;
  events only for effective future final-price changes after durable commit.
- #4: native per-site config/options editor for units, VAT inclusion/fraction,
  effective dates, verification/source, supplier, DSO, TSO, tax, subscriptions and
  heating eligibility. Manual locks, dated national baselines, verified Radius,
  last verified cache and explicit manual fallback. Public source diagnostics,
  applied-value UI summary, repair warnings, durable options/configuration audit,
  targeted future-only repricing from stored raw spot inputs, including offline
  edits when required DSO data is available. No inferred private/future terms.
- EWII historical household example: 0.030 DKK/kWh ex VAT from 2026-06-01 until
  2026-10-01 only. Not automatically applied; no summer-house rate or later contract
  is inferred. TSO baseline ends after 2026; uniform tax baseline ends after 2027.
- #5: versioned producer contract and separately reviewed EV consumer. Explicit
  external-site selection skips EV retrieval/calculation/storage/price sensors;
  copies final values; subscribes to revisions; fails closed on degraded/unloaded
  data with bounded discovery retry. Regular 30-minute planning and earliest-slot
  tie-break preserved. Existing legacy simulation sites do not migrate silently.

## Actual validation

Producer Python 3.14.8, hash-verified requirements-dev.lock, `.venv`:
**78 passed, zero skips, 92% coverage**. Ruff check/format clean. Official local
hassfest: **1 integration, 0 invalid**. Remote six checks green at code SHA above.

EV consumer, same locked Python environment and Node 24:
**153 passed, zero skips, 91% coverage** (adapter 98%). Ruff/format and official
local hassfest valid; remote six checks green at consumer code SHA above.
CI pins producer `f36250715eb3ec2e8a47424a780943192c96a634` for cross-repository tests.

Coverage includes native UI editing/discard/overlap, offline future repricing,
failed-write atomic rollback, restart/audit, 92/96/100-slot DST, source notification
coalescing/backoff/failure recovery, DSO automatic/manual-lock/fallback/unavailable,
site isolation and immutable consumer reads. Eight golden seasonal/DST/VAT scenarios
(768 slots) were generated from original pinned PR #12 code, not this producer.
Consumer tests exercise the real producer API/HA Store as well as Manager lifecycle
with local fetch and arithmetic forbidden. This is fixture parity, not live broker
or hardware acceptance. No live HA was used.

## Resume here / acceptance gaps

1. Read current PR reviews and exact-head checks; preserve existing changes. Do not
   rebuild the proven pricing/registry stack or repeat completed setup work.
2. Owner-provided read-only Energy Price Broker/real_energy_price input/output
   exports are required for actual household and summer-house parallel parity.
   No live HA/Node-RED access is authorized. Do not fabricate missing contract terms.
3. Review native UI usability in an owner-approved disposable HA instance; source
   and lifecycle tests use real HA test harness with mocked upstream services.
4. Measure multi-year/Raspberry Pi storage scale before production acceptance.
   Permanent HA Store snapshots/audit grow; ADR-001 documents SQLite migration as
   a measured follow-up, not hidden history pruning. Add broader DSO/source presets
   and future national rates only from verified authoritative data.
5. Consumer preview conservatively requests current quarter through next-day end;
   incomplete day-ahead prices defer new plans. Narrower deadline-scoped queries
   are a follow-up. No silent legacy fallback. Review PR #15 separately from #7.
6. No issue is auto-closed: developer preview is implemented, but broker parity,
   production acceptance, review and stable release remain outstanding.

## Reproduction and retained setup

From `/workspace/HA-Energy-Price-Engine`:

```sh
.venv/bin/pytest --cov=custom_components.ha_energy_price_engine
.venv/bin/ruff check custom_components tests tools
.venv/bin/ruff format --check custom_components tests tools
docker run --rm -v /workspace/HA-Energy-Price-Engine:/github/workspace ghcr.io/home-assistant/hassfest
gh pr checks 7 --repo NicolaiTandrup/HA-Energy-Price-Engine
```

The EV research checkout `/tmp/price-engine-research/ev-charge-manager` may be
transient. Recover `feat/price-engine-consumer` from its remote if absent. Read its
AGENTS.md/handoff. Run its suite with `PRICE_ENGINE_SOURCE` pointing to a producer
checkout; see docs/price-engine-consumer.md there for the exact CI pin.
Golden regeneration requires an unchanged original PR #12 source checkout at
`9d949c6d0905646d1bbf973ea2edb47846e1607d`; the generator refuses another HEAD.

Reusable install_script/start_skill are saved in the cloud environment draft:
Python 3.14.8, hash-locked dependency sync, existing-checkout workflow and mocked
HA validation. Installation/refresh commands were exercised and repeated. No
running service or secrets are required. Git read/push and GitHub API access work;
API/Datahub domains are saved. Run-log redirect host is restricted, but check-run
annotations are available and were sufficient for diagnosing the resolved HACS
brand failure. No verification or required CI checks were disabled.

Saving the environment draft does not publish it. Review/save the setup in
environment settings, then publish the cloud environment to retain a new snapshot
when desired; this is independent of integration release or production deployment.

No merge, stable release, production cutover, Node-RED baseline edits or live
Home Assistant/vehicle/charging controls have been performed or authorized.
