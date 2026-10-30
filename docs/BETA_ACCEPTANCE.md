# Beta.9 acceptance checklist

Software checks and owner Home Assistant acceptance are separate. Automated native
HA tests use recorded/synthetic provider boundaries and do not certify your private
contract, real provider availability or hardware performance. Exact results, source,
CI, package hashes and simulation screenshots are in the release receipt and
[permanent development handoff](https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/blob/feat/beta5-simple-onboarding/docs/DEVELOPMENT_STATUS.md).

## Software release gates

Beta.9-specific evidence is pending final validation; retained checks below also
cover the preserved beta.8 capabilities. The permanent handoff identifies each
completed run exactly.

- [ ] Native Done action, saved settings on close/reopen, no second Save/check.
- [ ] Real native desktop/mobile activation wait, first-quarter transition, and
  today-incomplete/tomorrow-Ready without backfill.
- [ ] Eight stored component diagnostic amounts, mixed VAT correctness, explicit
  next-quarter period, source/revision details and ordinary localized statuses.
- [ ] Beta.8 upgrade/restart preserves config, all old IDs, user choices and ledgers.
- [ ] New technical/unused provisional defaults off; explicit native opt-in/out.

- [x] Full producer suites on HA 2026.10.3 and current 2026.10.4, zero skips.
- [x] Unchanged consumer API suites and both actual runtime startup orders.
- [x] Official Nord Pool action/config discovery, automatic Radius C, bounded
  national rates, component expiry, negative prices and 92/96/100-quarter DST days.
- [x] Missing/incorrect supplier verification, explicit provisional approval,
  fail-closed API/ledger and raw source independence.
- [x] Step-confirmed persistence, interrupted native setup, unsubmitted changes, close/resume,
  actual persisted current-day readiness, storage failure and restart.
- [x] Native EN/DA desktop/mobile flows and local branding without PE image mocks.
- [x] Beta.1–.7 config, ledger rows, revisions, entity IDs and source references.
- [x] Confirmed permanent deletion, interrupted cleanup/retry, archive retention,
  clean reinstall and second-site/global recorder isolation.
- [x] Actual pinned HACS registration/tag install/update/uninstall/reinstall,
  authenticated channel repair, persisted beta state and semantic version reporting.
- [x] Hassfest, translations, HACS validation, clean deterministic packages and
  both ZIP layouts installed/imported outside the repository.
- [x] Exact-source green CI, immutable prerelease tag, public assets/source hashes
  and independent post-publication installation verification.

Publication software receipt: [beta.8 verification](https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/blob/feat/beta5-simple-onboarding/docs/receipts/v0.1.0-beta.9.json).
All software gates passed, including19 exact-source checks and fresh independent
public verification on both cores. All16 verification/orchestration jobs passed.
Published assets were not replaced during verification.
All owner acceptance items below remain unchecked.

- [x] Native HA and15 browser regression journeys: desktop/mobile graphs, complete
  tables, source/components/VAT parity, exact DSO merges, negative/zero prices,
  missing gaps, DST92/96/100, future revision updates and locale/XSS safety.
- [x] Authenticated site read permissions, bounded two-day responses, no provider/
  SQL/recomposition on dashboard reads, unchanged CM APIv1.
- [x] One-time unused optional estimate default disable, stable IDs/history, explicit
  user opt-in and configured provisional behavior; supported status localization.

## Your development HA acceptance

- [ ] Back up HA; record core/HACS/PE versions and storage/hardware.
- [ ] Update through HACS with **Show beta versions enabled**, restart and confirm
  manifest version **0.1.0-beta.9**. Existing site IDs/entities/history remain.
- [ ] Register the bundled local module in HA Resources; paste the complete
  [dashboard YAML](dashboard.yaml) changing one actual site entity ID. View both
  graphs, all quarter rows, today's DSO ranges and selected future components.
  Check local offsets/negative prices/gaps, source/VAT and current/history readiness.
- [ ] Confirm unused optional estimates no longer clutter the default device page.
  Canonical technical data remains in its original machine unit/state for compatibility.
- [ ] Verify official Nord Pool's actual area and daily quarter coverage without
  simultaneously running a legacy broker. Compare recorded legacy data offline.
- [ ] Confirm your real grid class, VAT and current supplier contract from a bill.
  Do not reuse historical household EWII terms for current or other sites.
- [ ] Complete the three-stage setup unaided in your chosen EN/DA interface language.
  Confirm each accepted step is Saved, close/reopen resumes, and numerical Review
  needs no final commit. Enter a fractional markup such as 0.25/0.50/0.75/3.125 øre with a point/comma,
  confirm VAT and verify there are no ordinary dates, fees, product/heating decisions.
- [ ] Confirm preferred raw/final/current/next/statistic prices use exactly 2 ore
  decimals or 4 DKK decimals, including your locale and negative prices. Canonical
  technical IDs/units/statistics remain. Check explicit entity/card precision overrides.
- [ ] Check a requested future window crossing midnight. Current/next/window can
  be READY while pre-activation full-day history remains honestly INCOMPLETE.
- [ ] Confirm raw READY coverage separately from final READY, one stored full
  breakdown and an offline bill comparison. Missing/expired dates have useful actions.
- [ ] If testing a provisional amount, confirm ESTIMATED/UNVERIFIED labels and
  consumer API INCOMPLETE; do not connect estimate sensors to charging controls.
- [ ] Confirm source publication, 13:05/13:20/13:40/23:59/00:01 refreshes and restart.
- [ ] Measure Pi resources/recovery on your hardware. Cloud timings are not Pi results.
- [ ] On disposable sites only, exercise retain-archive and confirmed permanent
  delete, restart/recreate, and preservation of another site's history.
- [ ] Confirm HACS installed/latest values are semantic beta versions after
  beta-channel repair/refresh. A missing external catalog icon is cosmetic.

No owner boxes are prechecked by software tests. No stable publication, main merge,
production cutover, vehicle command or charging-control acceptance is implied.

## Rollback and recovery

Keep full backups before upgrading. HACS uninstall preserves data. Restore the
matching program version and a known-good configuration/storage backup together
when necessary. Older software cannot read arbitrary future schemas; do not force
schema downgrades. Recover ledgers only offline using the documented
[storage procedure](ADR-002-ledger-storage.md); preserve referenced revisions and
compare records before resuming any separately managed consumers. PE never deletes
HA's global recorder database or external/full backups.
