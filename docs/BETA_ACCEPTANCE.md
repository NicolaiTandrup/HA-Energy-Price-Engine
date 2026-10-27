# PE + CM beta acceptance, source migration and rollback

Target: **v0.1.0-beta.3 read-only PE prerelease**. Publication is owner-authorized
once mandatory software checks pass; no stable, main merge or production cutover.

## Beta.3 software and owner acceptance

- [x] Real isolated native EN/DA new-site flows save complete verified fixtures.
- [x] Runtime final .6675 DKK/kWh / 66.75 øre, source .100, 96 quarters on both days.
- [x] Missing contract: raw 96 READY, final 0 INCOMPLETE, exact supplier period/action.
- [x] Radius/source/partial/ledger failures distinguished without manufacturing prices.
- [x] Actual beta.1/.2 source creates upgrade fixtures; ledger rows/revisions preserved.
- [x] Native user-language switch/fallback, submitted draft/Back/Discard/reload coverage.
- [x] HACS SHA fallback reproduced, beta subscription/semantic release behavior tested.
- [ ] Final exact-source both-core/consumer/HACS/hassfest/package CI.
- [ ] Published beta.3 source/assets verified independently on both cores.
- [ ] Owner PAHA02-DEV installation and focused [retest](WIZARD_GUIDE.md) recorded.
- [ ] Owner current contracts/source/billing and Raspberry Pi resource acceptance.

Beta.1/.2 automated software checks did **not** establish owner acceptance. Beta.3
simulations likewise do not check those owner boxes. Main is unchanged, PR unmerged,
no stable or control operation. Native Close does not submit typed fields: Continue
first. Entity names obey HA system language/registry; native enum states and wizard
follow individual user language. Technical provenance keys remain canonical.

## Before touching the owner's installation

- [ ] Record HA/PE/CM versions, exact commits, hardware/storage, explicit site IDs,
  provider integration entries and the selected controller for every charger/vehicle.
- [ ] Take a full known-good HA configuration/storage backup and export the exact
  Node-RED **Brain**, **Energy Price Broker** and **Charger Optimizer** flows,
  dependencies and current enable states. Verify the backup can be restored.
- [ ] Capture representative **recorded** legacy prices, legacy Nordpool inputs and
  known-good optimizer plans (including UTC timestamps, units and VAT convention).
  Compare offline against PE/billing fixtures. No simultaneous live brokers required.
- [ ] Obtain actual current per-site supplier terms and coverage. June–September
  2026 household EWII markup cannot establish October or summer-house terms.
- [ ] Review real CM command-executor capability/acknowledgment/session/guest/stale/
  plug-unplug/rate-limit safeguards separately. The tested consumer is not evidence
  of an authorized real charger transport. Keep commands disabled unless that gate
  and explicit owner authorization are independently satisfied.

## Offline comparison without parallel brokers

Normalize recorded exports to explicit site/currency/unit/VAT and timestamped final
amounts; never infer missing metadata from entity names or insert zero prices.
`docs/contracts/price-api-v1.examples.json` is synthetic format/conformance evidence,
not a household export. A verified ledger backup can be exported locally:

```sh
.venv/bin/python tools/ledger_backup.py export /path/to/verified-backup.sqlite3 \
  --site house --start 2026-09-01T00:00:00+00:00 --end 2026-09-02T00:00:00+00:00 \
  > /tmp/pe-recorded.json
.venv/bin/python tools/compare_recorded_prices.py /path/to/legacy-recorded.json \
  /tmp/pe-recorded.json --legacy-site legacy-house --candidate-site house \
  --start 2026-09-01T00:00:00+00:00 --end 2026-09-02T00:00:00+00:00
```

The comparison range and site mapping are explicit. Both inputs require `currency`
DKK, `unit` DKK/kWh, `vat_included: true`, `site_id`, and `slots` with aware `start`,
`end`, `final_price_incl_vat`. Known zero and negative prices are valid. Missing,
nonfinite, duplicate or wrong-unit inputs fail; gaps cannot become free quarters.
Exit 0 means complete match within the chosen tolerance; 1 means differences/gaps;
2 means invalid input. Default tolerance is 0.000001 DKK/kWh. Choose and justify
any invoice-rounding tolerance explicitly. Backup exports assert recorded amounts,
not current live READY/freshness. Keep private exports out of Git/CI artifacts.

## Owner-approved atomic source switchover

1. Obtain the owner's go-ahead for the scheduled installation, with rollback owner
   and abort thresholds agreed. Source migration and command permission are separate.
2. Stop/disable competing legacy paths only within that approved window, preserving
   their exact configuration and dependencies. Never leave two live controllers.
3. Migrate the legacy HACS Nordpool dependency to the official HA Nord Pool source
   as planned. Do not assume the legacy broker works when its old dependency is absent.
4. Install the reviewed PE/CM packages and explicit per-site mappings. Configure
   actual verified current contracts/DSO/TSO/tax/VAT; confirm current/next-day complete
   final prices and source verification. Unknown components must stay unavailable.
5. Verify 13:05 / 13:20 / 13:40 / 23:59 behavior, 00:01/startup/reconnection,
   restart persistence and measured/read-only optimization against recorded outputs.
   Current source validation can happen in the safe test setup or this window.
6. Keep CM read-only until its independent control gates and owner authorization
   pass. Activate only one controller per charger/vehicle if subsequently authorized.

Abort on wrong site/source, stale/incomplete/error prices, VAT/unit mismatch, failed
storage recovery, unsafe command ownership, unknown sessions/guest state, unacknowledged
commands or unacceptable resource behavior. A missing price is never a zero-cost plan.

## Rollback and history recovery

- Disable CM command paths first if they were explicitly commissioned. Preserve
  observations, price revisions and measured-cost records for diagnosis.
- Restore the full known-good HA/config/storage backup and **legacy Nordpool
  dependency** before relying on its broker. Restore the three exact saved Node-RED
  flows/dependencies/enable states only under the approved single-controller plan.
- Verify legacy sources, current prices, session ownership and known-good plans;
  then let the owner authorize resuming the one chosen controller.
- For isolated PE ledger recovery, prefer a coherent full HA backup. Stop the test
  HA before an explicit offline SQLite restore; compare backup revisions with CM
  recorded costs. A snapshot cannot recreate updates recorded after it.

Optional local administration (never run on an unapproved live HA):

```sh
.venv/bin/python tools/ledger_backup.py inspect /path/to/verified-backup.sqlite3
.venv/bin/python tools/ledger_backup.py restore /path/to/verified-backup.sqlite3 \
  /path/to/stopped-ha/.storage/ha_energy_price_engine.ENTRY.ledger.sqlite3 --confirm-offline
```

Restore verifies checksums/integrity and preserves previous destination bytes in a
separate file. Preserve original preview JSON files too. Do not downgrade only the
Python code while retaining a newer configuration/database schema. Never silently
rewrite settled CM costs or substitute a newer price revision for an applied one.

## Evidence still required from the owner

Recorded household/summer-house legacy/billing exports; actual current contract
terms; approved HA OS/Raspberry Pi resource/source validation; independent real
command-executor acceptance if control is desired; and explicit publication/cutover
authorization. These are distinct from the automated software checks. No permanent
ban on an eventual controlled replacement is implied; no actual switch occurred.
