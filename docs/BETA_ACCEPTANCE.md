# Beta.5 acceptance checklist

Software checks and owner Home Assistant acceptance are separate. Automated native
HA tests use recorded/synthetic provider boundaries and do not certify your private
contract, real provider availability or hardware performance. Exact results, source,
CI, package hashes and simulation screenshots are in the release receipt and
[permanent development handoff](DEVELOPMENT_STATUS.md).

## Software release gates

- [ ] Full producer suites on HA 2026.10.3 and current 2026.10.4, zero skips.
- [ ] Unchanged consumer API suites and both actual runtime startup orders.
- [ ] Official Nord Pool action/config discovery, automatic Radius C, bounded
  national rates, component expiry, negative prices and 92/96/100-quarter DST days.
- [ ] Missing/incorrect supplier verification, explicit provisional approval,
  fail-closed API/ledger and raw source independence.
- [ ] Step-confirmed persistence, interrupted native setup, unsubmitted changes, Back/Resume,
  actual persisted current-day readiness, storage failure and restart.
- [ ] Native EN/DA desktop/mobile flows and local branding without PE image mocks.
- [ ] Beta.1–.4 config, ledger rows, revisions, entity IDs and source references.
- [ ] Confirmed permanent deletion, interrupted cleanup/retry, archive retention,
  clean reinstall and second-site/global recorder isolation.
- [ ] Actual pinned HACS registration/tag install/update/uninstall/reinstall,
  authenticated channel repair, persisted beta state and semantic version reporting.
- [ ] Hassfest, translations, HACS validation, clean deterministic packages and
  both ZIP layouts installed/imported outside the repository.
- [ ] Exact-source green CI, immutable prerelease tag, public assets/source hashes
  and independent post-publication installation verification.

Publication software receipt: [beta.5 verification](receipts/v0.1.0-beta.5.json).
Software gates are checked only after final exact-source validation/public verification.
All owner acceptance items below remain unchecked.

## Your development HA acceptance

- [ ] Back up HA; record core/HACS/PE versions and storage/hardware.
- [ ] Update through HACS with **Show beta versions enabled**, restart and confirm
  manifest version **0.1.0-beta.5**. Existing site IDs/entities/history remain.
- [ ] Verify official Nord Pool's actual area and daily quarter coverage without
  simultaneously running a legacy broker. Compare recorded legacy data offline.
- [ ] Confirm your real grid class, VAT and current supplier contract from a bill.
  Do not reuse historical household EWII terms for current or other sites.
- [ ] Complete the five-stage setup unaided in your chosen EN/DA interface language.
  Confirm each accepted step is Saved, close/reopen resumes, and numerical Review
  needs no final commit. Check a public offer against your actual agreement or
  enter custom øre/kWh/VAT/monthly terms without dates.
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
