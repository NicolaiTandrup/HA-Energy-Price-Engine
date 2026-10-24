# Development handoff

Updated 2026-10-24. Read AGENTS.md first; this is the single permanent handoff.

## Active work

Branch: `feat/standalone-price-engine`, based on `981e489` (main).
Last pushed validated producer: `f362507` (all six remote CI checks green).
Earlier native producer `3f7f684`; pricing core `5eb20de`; workflow `e50d0df`.
Draft PR: https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/pull/7.
Current checkpoint subject: `test: verify native tariff modes and consumer interoperability`.
Previous hardening code: `a5cf2c2` (74 local tests, 91% coverage).

## Completed and in progress

- #1 developer-preview domain, per-site HA entries, lifecycle, sensors, ADR-001,
  public API v1, README, attribution, permanent workflow and CI definitions.
- #2 ported atomic HA Store ledger, immutable indexed UTC lookups, permanent history
  (upstream had 365-day retention), durable old/new future-correction audit,
  batch signatures, failed-write protection and settled-history preservation.
- #3 preserved all Copenhagen schedule times, startup recovery, complete-day
  validation, operational statuses/counts, future-price-only revision events.
- #4 native per-site config/options rate editor with explicit units/VAT/dates/source,
  manual locks, bounded national baselines, Radius source/cache, manual fallback,
  subscriptions and heating eligibility. No inferred EWII or summer-house default.
  The household example is 0.030 DKK/kWh ex VAT, June–September 2026 only.
- Diagnostics redact names/IDs/free-form source references. Native options show
  applied values/source/periods/check/change, repair warnings show missing coverage.
- #5 producer contract tests include isolated site mapping, degraded/unloaded API,
  earliest-slot consumer ranking and shared upstream calculation fixtures. A separate EV consumer implementation is locally validated (153 tests);
  broker-export comparisons remain pending.

## Validation

Python 3.14.8, `.venv`, hash-verified upstream requirements-dev.lock.
`pytest --cov=custom_components.ha_energy_price_engine --cov-report=term-missing`:
**78 passed, zero skips, 92% coverage**. Ruff check/format passed.
Official `ghcr.io/home-assistant/hassfest` local validation: **1 integration,
0 invalid**, including config flow/translations/manifest. No live HA was used.
All SIX exact-head remote push/PR checks (tests, hassfest, HACS) passed
at `f36250715eb3ec2e8a47424a780943192c96a634`; earlier tests/hassfest passed at `3f7f684`. HACS failed
because a local brand icon was missing; this checkpoint supplies that asset.
The HACS fix is confirmed at `f362507`; new exact-head checks must be rechecked
after this checkpoint is pushed. The optional categories field was tested and removed
because official hassfest rejected the speculative value. The subsequent local
run caught the required domain/name-first key ordering; this checkpoint restores it.
No required check is disabled.

## Access and decisions

Git read/push works for Price Engine; GitHub HTML reads work for both repositories.
GitHub API access recovered after the saved network configuration; gh now works. `api.github.com` and optional public
`api.energidataservice.dk` saved in the environment draft; user-facing save is needed
for runtime policy propagation. No credentials requested or invented. Draft PR #7 created and meaningful progress comment posted. Run-log download
redirects use an additional host blocked by the proxy; check-run annotations are
available via api.github.com and were sufficient to diagnose the HACS failure.

Reuse EV Manager PR #11 (`5c32dc9`) and #12 (`9d949c6`, substantive `6f972a5`),
not their vehicle/control stack. Source research checkout at
`/tmp/price-engine-research/ev-charge-manager` is disposable; Git provenance is in
PROVENANCE.md. One canonical handoff only. ADR/API docs define ownership/boundaries.

## Next steps

1. Hardening complete: offline targeted future-edit/old-new audit, disk rollback,
   source debounce/backoff and persistent failure state, UI add/remove/taxes/DSO,
   bounded EWII dates, per-day no-recomposition signatures and permanent retention.
   Golden fixtures generated using the original pinned PR #12 code verify every
   slot across eight seasonal/DST/VAT scenarios (not live broker parity).
2. Full producer suite now 78 tests with native automatic/locked/manual-fallback/
   unavailable DSO lifecycle tests. Added public source verification diagnostics,
   active-period signature filtering and locked-DSO offline-edit support.
   Verify final remote CI after push.
3. Inspect push CI via GitHub HTML if API remains blocked; create draft PR and post
   progress comments once api.github.com access is available. Never claim pending CI.
4. A separate EV consumer branch `feat/price-engine-consumer` is in progress in
   the research checkout, based on original PR #12. It explicitly selects an
   external producer site, skips legacy source scheduling/calculation/publishing,
   copies final values and fails closed. Consumer code `088c8fa` has **153 passed,
   zero skips, 91% coverage**, Ruff/format and official local hassfest valid.
   Separate draft: https://github.com/NicolaiTandrup/HA-EV-Charge-Manager/pull/15
   (based on PR #12). Consumer push tests/hassfest/HACS passed at `088c8fa`;
   PR-triggered counterparts were still running at the last check. Recheck all
   exact-head checks before reporting final CI.
5. Obtain owner-provided read-only broker comparison exports for #5; fixture parity
   alone does not prove live household parity. Do not contact running HA/Node-RED.
6. Performance measurement/storage migration for multi-year large deployments,
   authoritative future rates and production/hardware acceptance are follow-ups.

Reusable environment install_script and start_skill are saved for Python 3.14.8,
hash-locked dependency sync, existing-checkout startup and mocked HA validation.
Commands were exercised/repeated successfully. No running service is required.
Saving the draft is not publication; review/save/publish environment settings to
retain a new snapshot when desired, independently of integration releases.

No merge, stable release, production cutover or live controls have been performed.
