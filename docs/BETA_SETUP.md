# Install and configure v0.1.0-beta.1

Use the [exact HACS / PAHA02-DEV procedure](HACS_DISTRIBUTION.md) to add the PE
repository as Integration and select **v0.1.0-beta.1** with beta versions enabled.
The owner authorized the PE main merge and prerelease on 2026-10-26. Check the public
release/verification receipt for its validated commit. No CM publication or production
change is part of that authorization. Everyday pricing setup is native UI, not YAML.

## Choose an isolated installation and exact package

Use a disposable/current supported 64-bit HA installation first. Current HA
2026.10.4 and the fixture-supported 2026.10.3 are exercised in CI. Take a full HA
backup before installation or upgrade. Real Raspberry Pi resource/source acceptance
is still required; [cloud measurements](PERFORMANCE.md) are not Pi measurements.

For manual placement, download the published prerelease assets and checksums.
Developers can reproduce the exact clean release checkout with:

```sh
.venv/bin/python tools/build_beta.py
```

`dist/BUILD_MANIFEST.json` records version, full source commit, dirty state and each
runtime file hash; `dist/SHA256SUMS` verifies both archives. Production/reviewable
candidates must say `dirty: false`. `--allow-dirty` exists only for development tests.
No build command creates a tag, GitHub release or deployment.

| Archive | Extract into | Result |
| --- | --- | --- |
| `ha_energy_price_engine-manual.zip` | HA configuration directory | `custom_components/ha_energy_price_engine/manifest.json` |
| `ha_energy_price_engine.zip` | `custom_components/ha_energy_price_engine/` | Same files, with the root layout HACS expects for a release asset |

Do not extract the HACS-root ZIP at HA's configuration root. Do not copy development
venvs, tests, dependency locks or consumer-reference exports into HA. Restart the
**approved test instance** after installing/updating custom integration code.

The source tree has HACS metadata/brand assets. HACS uses the selected published tag's
`custom_components/ha_energy_price_engine` directory; manual placement of a ZIP is an
alternative, not a prerequisite or custom-repository URL. See HACS_DISTRIBUTION.md
for beta visibility, updates and independently verified public download details.

## Official Nord Pool prerequisite and safe discovery

Configure the **official Home Assistant Nord Pool** integration according to its
[HA documentation](https://www.home-assistant.io/integrations/nordpool/), selecting
the site's area. PE uses its read-only `get_prices_for_date` response in DKK/MWh
excluding VAT and normalizes it once. It needs no separate PE credentials.

The old HACS Nordpool component can shadow the same `nordpool` domain. PE checks
that the selected implementation is built into HA and rejects a legacy custom
component. **Do not run the old broker and the official source simultaneously as
an acceptance requirement.** Use a fresh test instance, recorded legacy exports,
or the owner-approved atomic switchover in [BETA_ACCEPTANCE.md](BETA_ACCEPTANCE.md).
Do not remove/disable anything on live HA merely to try this candidate.

## Add independent sites in Devices & services

1. Open **Settings → Devices & services → Add integration → Energy Price Engine**.
2. Enter a readable site name and a stable lowercase ID, for example `house` or
   `summer_house`. That ID/config entry is the explicit consumer mapping; renaming
   the label does not change its identity.
3. Choose **Official Nord Pool** and its config entry. One unambiguous existing
   official entry is suggested for confirmation; multiple entries require a choice.
   Confirm the price area (`DK2` initially) and `Europe/Copenhagen` for a Danish
   delivery day. Official input is ex-VAT `DKK/MWh`; confirm the VAT fraction
   (`0.25` means 25%). No supplier contract is discovered or copied.
4. Add the entry, then open its **Options / Configure** menu to enter dated business
   rates below. Until required components cover the current day, readiness is
   degraded and the current price is unknown, never a fabricated zero.
5. Repeat Add integration for each additional site. HA's integration entry/device
   list is the site list; there is no hardcoded site count. Each entry has its own
   source mapping, rules, ledger and diagnostics. Resource use still scales with data.

Use Options → Site or HA's Reconfigure action to change a source/label/area without
changing the stable ID. Use HA's Delete entry action to remove a site. Other sites
continue working. Authoritative price history is retained for references; a new
entry never silently inherits the removed site's private rates/history.

## Pricing / tariffs / supplier / taxes

Every dated rule has component, amount, explicit money unit, VAT inclusion/fraction,
source reference, verification date, inclusive start date and **exclusive end date**.
No address, account number or secret belongs in a source reference.

| Menu/component | Configure |
| --- | --- |
| Supplier | Choose EWII or Custom as a label, then add the actual dated supplier markup. Selecting EWII installs no contract value. |
| Grid / DSO | Verified Radius **C** automatic source, or explicit dated manual DSO rules for the verified category. Other automatic classes are rejected. |
| Energinet network/system | Explicit dated values, or opt into the documented bounded national baseline: 2026 ex-VAT 0.043 / 0.072 DKK/kWh. This is not live legislative discovery. |
| Electricity tax | Explicit dated rules or the documented ex-VAT 0.008 DKK/kWh 2026–2027 baseline. No 2028 rule is invented. Heating eligibility also requires a verified rule, registration, usage year and threshold evidence. |
| Subscriptions | Separate supplier/grid monthly rules in DKK/month; never amortized into marginal slot prices. |

**EWII historical household fact only:** 0.030 DKK/kWh excluding VAT from
2026-06-01 until **2026-10-01**, covering June–September 2026. It is not a current
October rate and not a summer-house contract. Supply the actual current per-site
contract/effective period; the integration cannot manufacture it.

For time-of-use manual tariffs, create separate dated DSO rules and select their
**local hours**. Blank hours means all day. Same-priority overlapping periods/hours
are rejected, and missing bands do not become zero. Both repeated autumn hours and
the short spring day are handled by UTC interval identity plus local clock selection.

A manual lock takes precedence over automatic component baselines. An automatic
Radius outage retains only a sufficiently recent, coverage-verified cache; explicit
manual fallback requires valid dated DSO rules and is labelled degraded. It does
not silently certify an old/fallback tariff as fresh automatic data. Deliberately
select authoritative manual mode after verification when appropriate.

To schedule a new contract, edit the old end date to the new start date and add the
new period in the **same options draft**, then Save. Closing without Save discards
staged edits. Changing rates reprocesses affected future quarters; already-started
prices stay unchanged and prior published revisions remain recoverable. Amounts are
normalized with VAT exactly once. No source-code edits are necessary.

## Optional provider-neutral entity source

Select a sensor explicitly and confirm unit (`DKK/kWh`, `DKK/MWh` or `ore/kWh`),
price basis (spot excluding/including VAT, or final all-in) and interval attribute.
The entity must expose timestamped start/end/price rows, `currency: DKK`, matching
`unit_of_measurement`, boolean `vat_included`, and an offset-aware provider
`verified_at`. Missing/stale/future verification or mismatched conventions fail
closed. HA report time alone is not verification. PE output cannot source itself.
Final all-in mode prohibits tariff/VAT additions; use spot mode for composed rates.

## Check readiness, sources and persistence

Each site publishes seven entities: current and next-quarter final DKK/kWh,
complete-day minimum/maximum/average, current readiness and tomorrow readiness.
Incomplete/stale days have no numeric aggregate. Readiness attributes show source
title, site, DK2/DKK, 15-minute resolution, coverage, last verification/error and
next scheduled check. Options → Inspect a stored quarter-hour price explains a
selected today/tomorrow slot including VAT and original revision, with unambiguous
local UTC offsets on repeated autumn hours. No source calls or tariff composition
occur on these reads. Dashboard reads
and API v1 lookups never fetch sources or calculate tariffs. Diagnostics and Options
show applied components, periods/locks, verification, revisions, valid/expected slot
counts and public source provenance. Names/free-form source references are redacted
from downloadable diagnostics. Repairs rechecks only clear the warning after READY.

Expect 96 quarters normally, 92 spring, 100 autumn. Negative prices are valid.
READY is verified complete coverage; INCOMPLETE is missing/rejected coverage; STALE
retains values with degraded/expired verification; ERROR is failed source/storage
verification. Consumers must not use missing/stale/error data as free electricity.

Copenhagen refresh times remain 13:05; conditional 13:20 / 13:40 / 23:59; unconditional
00:01 for the newly started day, plus startup recovery and bounded source-event
verification. Late provider startup, reload and new source entities trigger recovery
without waiting for the next afternoon publication. Midnight display/readiness uses the new date before the 00:01 sync.

Reload the entry and restart the approved test HA to confirm persistence. Native
Options → Storage can create a verified SQLite snapshot. Valid preview JSON ledgers
migrate once to SQLite without deleting the original; corrupt history blocks writes
rather than silently starting over. See ADR-002 and the recovery checklist.

## Consumer and testing references

Map CM explicitly to this PE entry/site. PR #15 uses `price_engine_site`; reconciled
measured-history PR #16 uses `producer_entry` / `producer_site`. Neither consumer
may fetch markets, apply VAT/tariffs or silently fall back to embedded production.
API v1 and machine-tested fixtures are documented in [API.md](API.md).

Local development uses Python 3.14.8, hash-locked dependencies and pinned consumer
exports (`tools/prepare_consumer_refs.py`). The current-HA lock deliberately tests
2026.10.4 using fixture 0.13.374's documented HA-version override until its next
matching release; the normal fixture-supported lock uses 2026.10.3. This affects
test scaffolding only, not the deployed integration's runtime dependencies.

Passing these automated tests does not approve real charging control or prove live
provider availability. Complete the [acceptance and rollback checklist](BETA_ACCEPTANCE.md)
with the owner before a real source/controller switchover.
