# Install and configure v0.1.0-beta.3

Use the [exact HACS / PAHA02-DEV procedure](HACS_DISTRIBUTION.md) to add the PE
repository as Integration and select **v0.1.0-beta.3** with beta versions enabled.
The owner authorizes beta.3 prerelease publication after mandatory checks. Main
already supports HACS registration; beta.3 installs from its exact tag without
merging its development PR. No production or control operation is included.
Everyday pricing setup is native UI, not YAML.

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

Follow the [illustrated six-stage wizard](WIZARD_GUIDE.md), available both from
**Add integration** and an existing site's **Configure / Options**:

1. **Site and source**: enter a name; leave the optional ID blank for a unique
   generated ID. Choose official Nord Pool, select its readable entry, confirm the
   supported area/timezone hints. Input conventions are automatic **DKK/MWh ex VAT**.
   The spot/grid VAT field is **25** for 25%, not 0.25.
2. **Grid**: confirm Radius C before selecting automatic verification, or choose
   explicit manual rates. No grid product is inferred from a supplier label.
3. **Supplier**: choose EWII/custom as a label. To add a contract, explicitly enter
   your verified amount, unit, VAT and bounded dates/source. Leaving Add contract
   off retains existing periods and allows an incomplete site to be saved.
4. **National charges**: explicitly opt into documented bounded national rules or
   use manual dated rules. Heating registration never creates a guessed discount.
5. **Display**: default **øre/kWh**; canonical DKK entities, storage and API stay
   unchanged. Separate display entities have unit-specific identities.
6. **Review, Save & verify**: inspect coverage by date. Open **Dated rates / manual
   overrides** for advanced edits, then return to Review and choose **Save & verify**.
   Saved configuration is not a claim of READY prices.

On forms select **Next / Back / Review**, then **Continue**. Continue persists a
draft without applying active changes; closing and reopening resumes it. Every page
warns that **Close/browser reload does not submit fields still being typed**: press
Continue first. Validation errors and submitted Back edits are retained; Save returns
to pending pages before applying them. **Discard draft…** requires explicit confirmation.
Do not edit the same site in multiple browser flows at once.

Repeat Add integration for independently configured sites; there is no hardcoded
count. Existing incomplete sites resume through Configure. Site renaming preserves
its permanent ID; source changes preserve its entry/history. Delete uses HA's
entry menu; retained accounting ledgers are never automatically assigned to a new entry.

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
new period in the **same options draft**, then return to Review and **Save & verify**. Submitted changes persist in a
separate draft across closing; active pricing remains unchanged until final Save. Changing rates reprocesses affected future quarters; already-started
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

Each site preserves the seven original canonical/readiness entities: current and next-quarter final DKK/kWh,
complete-day minimum/maximum/average, current readiness and tomorrow readiness.
Incomplete/stale days have no numeric aggregate. Readiness attributes show source
title, site, DK2/DKK, 15-minute resolution, coverage, last verification/error and
next scheduled check. Configure → Review → Dated rates / manual overrides → Inspect a stored quarter-hour price explains a
selected today/tomorrow slot including VAT and original revision, with unambiguous
local UTC offsets on repeated autumn hours. Five additional preferred-display sensors default to øre/kWh, while the original
DKK sensors keep their IDs and statistics. Switching preference creates the other
unit family; it never reinterprets old statistics. Device info shows the installed
manifest version. Missing-component attributes identify date, source and corrective
action. No source calls or tariff composition
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

## Beta.3 raw source versus final price

New raw current/next **DKK/kWh before additions** and today/tomorrow raw-source enum
sensors expose actual verified quarters and timestamps independently from final
composition. Official DKK/MWh is converted once; 100 DKK/MWh becomes 0.100 DKK/kWh.
Raw spot is never a total electricity price. An all-in entity provider is not falsely
labelled raw spot. No raw quarter is fabricated. Raw observations are operational
and bounded to recent days; authoritative final SQLite history retains its existing
policy. On restart raw observations are fetched again, not invented from final totals.

The new localized final status and pricing-problem entities give corrective guidance.
Existing uppercase readiness codes and canonical DKK entities/API remain compatible.
Missing supplier/national periods are INCOMPLETE, with component/date/action; source,
Radius and storage failures are distinct. Final valid_slots counts final records,
not raw provider input. Raw READY 96 + final INCOMPLETE 0 is legitimate when a required
contract is missing. Cached raw source can be STALE after a failed refresh, retains
its original timestamp, and expires within two hours; final API remains fail-closed.

New Danish official-source sites suggest the documented bounded national baseline
with a visible editable checkbox. Existing choices/overrides remain unchanged. No
Radius connection is inferred merely from DK2: confirm the grid product. No private
EWII amount or heating eligibility is defaulted.

Review uses the actual source adapters and the same canonical calculate() function
in a transient in-memory sink; drafts never write price ledgers. Save rechecks and
applies the complete configuration through normal runtime/transactional persistence.
Preview calculation success is not proof that a later disk write succeeded: inspect
final status/problem and verified slot counts after Save. Storage failures retain
old history and identify disk/recovery action. There is no extra hidden Save.

Native English/Danish forms, selectors, validation, Repairs and enum states follow
the user's selected UI language. HA entity names follow the **system language** and
existing registry names, as standard native HA behavior; changing a user's profile
does not rename entities for everyone. Both name resources are shipped. New enum
status entities localize per user; legacy uppercase state codes remain unchanged.
Technical details retain canonical source/API keys and provider exception text.
