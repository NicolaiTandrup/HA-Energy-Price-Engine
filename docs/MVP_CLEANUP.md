# Beta.10 MVP inventory and implementation decision

Inventory recorded **before runtime implementation**, 31 October 2026 (Europe/Copenhagen).
Baseline published beta.9 source `6c588323786cc5f8f696d553e02213ef8b169286`; development checkpoint `420eeb36d6f7a517b52e4462971d8ef19f68648f`. Issue #15 owner update explicitly permits breaking entity/config/API changes.

Measured construction: **40 sensor entities +1 PE update entity/site**; **37 runtime Python modules / 7214 lines**; 876821 runtime bytes, including 546588 translation/string bytes. Counts include disabled/hidden identities. Existing HACS update entities are separate and excluded.

## Essential product and boundaries

Preserve verified official Nord Pool quarters, Radius C/date/hour bands, bounded national charges, confirmed supplier markup, tax/VAT, negative prices, UTC/DST, transactional compressed SQLite, interval revisions, per-site isolation, scheduled refresh, one read-only card and a fail-closed consumer range API. Retain supplied-quarter kWh variable cost estimation. No household invoices, monthly subscriptions, provisional prices or automatic private-contract guessing.

## Complete entity audit

`site_` denotes the site ID prefix; the display-unit suffix can also be `_dkk` in beta.9. CM reads the Python API and references **none** of these sensor identities. The beta.8/9 card can use any PE registry entity as a permission/discovery anchor; that technical-ID requirement is retired.

| Beta.9 unique ID | Enabled default | Recorder/statistics | Purpose/reference | MVP decision |
|---|---|---|---|---|
| `site_current_price` | false | HA state + long-term measurement statistics | Canonical DKK duplicate; optional automation/Recorder reference | Retire duplicate; one ore identity per primary value |
| `site_estimated_price_0` | only with provisional config | HA state history only | Unverified estimate, not API/ledger | Retire provisional pricing |
| `site_estimated_price_1` | only with provisional config | HA state history only | Unverified estimate, not API/ledger | Retire provisional pricing |
| `site_raw_spot_0` | false | HA state history only | Canonical DKK duplicate; optional automation/Recorder reference | Retire duplicate; one ore identity per primary value |
| `site_raw_spot_1` | false | HA state history only | Canonical DKK duplicate; optional automation/Recorder reference | Retire duplicate; one ore identity per primary value |
| `site_raw_readiness_0` | true | HA state history only | Native diagnostic only | Merge into one availability sensor/attributes |
| `site_raw_readiness_1` | true | HA state history only | Native diagnostic only | Merge into one availability sensor/attributes |
| `site_final_status` | true | HA state history only | Native diagnostic only | Merge into one availability sensor/attributes |
| `site_next_quarter_status` | true | HA state history only | Native diagnostic only | Merge into one availability sensor/attributes |
| `site_historical_day_status` | true | HA state history only | Native diagnostic only | Merge into one availability sensor/attributes |
| `site_pricing_problem` | true | HA state history only | Native diagnostic only | Merge into one availability sensor/attributes |
| `site_readiness` | false | HA state history only | Uppercase legacy alias; redundant native status | Retire alias |
| `site_next_price` | false | HA state + long-term measurement statistics | Canonical DKK duplicate; optional automation/Recorder reference | Retire duplicate; one ore identity per primary value |
| `site_today_minimum` | false | HA state + long-term measurement statistics | Canonical DKK duplicate; optional automation/Recorder reference | Retire duplicate; one ore identity per primary value |
| `site_today_maximum` | false | HA state + long-term measurement statistics | Canonical DKK duplicate; optional automation/Recorder reference | Retire duplicate; one ore identity per primary value |
| `site_today_average` | false | HA state + long-term measurement statistics | Canonical DKK duplicate; optional automation/Recorder reference | Retire duplicate; one ore identity per primary value |
| `site_tomorrow_status` | false | HA state history only | Uppercase legacy alias; redundant native status | Retire alias |
| `site_tomorrow_readiness` | true | HA state history only | Native diagnostic only | Merge into one availability sensor/attributes |
| `site_current_availability` | true | HA state history only | Native diagnostic only | Merge current/tomorrow/history into one actionable availability with coverage attributes |
| `site_tomorrow_availability` | true | HA state history only | Native diagnostic only | Merge current/tomorrow/history into one actionable availability with coverage attributes |
| `site_history_availability` | true | HA state history only | Native diagnostic only | Merge current/tomorrow/history into one actionable availability with coverage attributes |
| `site_prices_start_at` | only with pricing_start | HA state history only | Native diagnostic only | Merge exact activation into availability/details |
| `site_breakdown_period` | true | HA state history only | Native diagnostic only | Merge period into compact component details |
| `site_component_spot_ore` | true | HA state history only | Individual stored component, duplicated in card | Merge into compact component attributes/card; retain current DSO numeric sensor |
| `site_component_dso_ore` | true | HA state history only | Individual stored component, duplicated in card | Merge into compact component attributes/card; retain current DSO numeric sensor |
| `site_component_energinet_net_ore` | true | HA state history only | Individual stored component, duplicated in card | Merge into compact component attributes/card; retain current DSO numeric sensor |
| `site_component_energinet_system_ore` | true | HA state history only | Individual stored component, duplicated in card | Merge into compact component attributes/card; retain current DSO numeric sensor |
| `site_component_supplier_ore` | true | HA state history only | Individual stored component, duplicated in card | Merge into compact component attributes/card; retain current DSO numeric sensor |
| `site_component_electricity_tax_ore` | true | HA state history only | Individual stored component, duplicated in card | Merge into compact component attributes/card; retain current DSO numeric sensor |
| `site_component_vat_ore` | true | HA state history only | Individual stored component, duplicated in card | Merge into compact component attributes/card; retain current DSO numeric sensor |
| `site_component_final_ore` | true | HA state history only | Individual stored component, duplicated in card | Merge into compact component attributes/card; retain current DSO numeric sensor |
| `site_display_current_ore` | true | HA state history only | Ordinary numeric sensor; no statistics class | Keep semantic current/next/raw/average/min/max once in fixed ore2 |
| `site_display_next_ore` | true | HA state history only | Ordinary numeric sensor; no statistics class | Keep semantic current/next/raw/average/min/max once in fixed ore2 |
| `site_display_minimum_ore` | true | HA state history only | Ordinary numeric sensor; no statistics class | Keep semantic current/next/raw/average/min/max once in fixed ore2 |
| `site_display_maximum_ore` | true | HA state history only | Ordinary numeric sensor; no statistics class | Keep semantic current/next/raw/average/min/max once in fixed ore2 |
| `site_display_average_ore` | true | HA state history only | Ordinary numeric sensor; no statistics class | Keep semantic current/next/raw/average/min/max once in fixed ore2 |
| `site_display_raw_current_ore` | true | HA state history only | Ordinary numeric sensor; no statistics class | Keep semantic current/next/raw/average/min/max once in fixed ore2 |
| `site_display_raw_next_ore` | true | HA state history only | Ordinary numeric sensor; no statistics class | Keep semantic current/next/raw/average/min/max once in fixed ore2 |
| `site_display_estimated_current_ore` | only with provisional config | HA state history only | Ordinary numeric sensor; no statistics class | Retire provisional pricing |
| `site_display_estimated_next_ore` | only with provisional config | HA state history only | Ordinary numeric sensor; no statistics class | Retire provisional pricing |

The per-site `Published PE release` update entity is also retired. HACS remains responsible for updates. Removed beta entities are not created and hidden. Schema4 requires explicit reset of old beta sites; no automatic deletion of unrelated entities, other sites, or Recorder.

### Planned primary surface

| Sensor | Unit/role |
|---|---|
| Spot now / spot next quarter | 2 sensors, ore/kWh2, source verification |
| Final now / final next quarter | 2 sensors, ore/kWh2, verified records only |
| Today average / minimum / maximum | 3 sensors, ore/kWh2; explicit full-day or remaining-day scope/coverage |
| Current DSO tariff | 1 sensor, ore/kWh2; actual resolved stored current component |
| Price availability | 1 diagnostic status; current/next/tomorrow counts, statistics scope, action, exact first price, compact 8-component snapshot |

**Target:9 sensors/site**, no PE-owned update entity, no canonical/display duplication, no per-quarter entities. Individual component amounts and sources remain in native attributes and selected-quarter card table.

## All runtime modules

| Module (beta.9 lines) | Decision |
|---|---|
| `__init__.py` (131) | Keep native setup/unload; replace v1–3 migration with explicit v4 reset gate. |
| `adapters.py` (36) | Legacy entity/raw_today/hour-expansion adapter; replace strict official source normalization in prices. |
| `api.py` (241) | Replace preliminary v1/serialization/producer aliases with compact v2 immutable range/slot contract. |
| `charging_cost.py` (71) | Keep verified supplied-kWh variable EV cost estimation; adapt v2, no billing/accounting GUI. |
| `charging_diagnostics.py` (163) | Redundant Options breakdown/horizon/session screens; card and compact status cover them. |
| `component_status.py` (384) | Parallel diagnostic resolution and retired Review/menu presentation. |
| `config_flow.py` (482) | Replace legacy hierarchy with one small saved-step ConfigFlow/Options mixin. |
| `configuration.py` (171) | Reduce to official Nord Pool + Radius/manual + dated marginal rates; reject retired fields. |
| `const.py` (15) | Keep minimal domain/API/component constants. |
| `contracts.py` (91) | Catalogue/monthly/provisional contract replacement scaffolding; use ordinary confirmed marginal rule. |
| `coordinator.py` (254) | Keep independent site ownership, source-change debounce and events; remove optimizer shim/config audit/legacy entity source. |
| `dashboard.py` (265) | Keep bounded permission-checked stored schedule; simplify discovery/config and use one new API. |
| `device_diagnostics.py` (161) | Thirteen extra diagnostic sensors/helper scope; merge read-only facts into shared status. |
| `diagnostics.py` (128) | Keep compact redacted operational download, consolidate duplicate breakdown paths. |
| `estimates.py` (38) | Unverified visualization-only alternate pricing path does not belong in MVP. |
| `flow_tools.py` (125) | Legacy selectors/management/HACS repair mixin; retired with old flow. |
| `hacs_channel.py` (80) | PE should not own HACS repository/beta metadata repair. |
| `ledger.py` (372) | Keep compressed transactional SQLite, checksum/revision/recovery/backup implementation. |
| `localization.py` (74) | Keep only authenticated user language/native labels actually used. |
| `models.py` (36) | Keep UTC quarter-hour value types and strict interval validation. |
| `money.py` (26) | Keep precise markup parsing and per-kWh conversion; remove monthly units. |
| `presentation.py` (27) | Canonical/display/DKK preference identities retired; ordinary sensor formatting is native HA ore2. |
| `price_components.py` (203) | Keep single dated marginal calculation/VAT/overrides; remove subscriptions and annual-use eligibility. |
| `price_engine.py` (371) | Keep authoritative precalculation/index/revisions; remove flat/all-in calculation and legacy JSON import/unused attributes. |
| `price_schedule.py` (171) | Keep 13:05/13:20/13:40/23:59/00:01 scheduling; remove optimizer site wrapper. |
| `price_update.py` (359) | Keep update-only fetch/verification/persistence; remove entity/all-in/fallback/provisional paths. |
| `prices.py` (117) | Keep official adapter/cache, consolidate discovery and strict normalization. |
| `repairs.py` (36) | Keep only if it provides an actionable native repair route, otherwise merge into flow/status. |
| `sensor.py` (735) | Replace 40 identities/preferences machinery with 9 primary sensors and bounded component attributes. |
| `simple_setup.py` (1012) | 1012-line overlay on legacy flow; replace, not move. |
| `site_lifecycle.py` (120) | Keep explicit scoped reset safety; remove archive/draft feature machinery. |
| `sources.py` (60) | Entity source conventions retired; consolidate official source discovery into prices. |
| `status.py` (146) | Consolidate shared read-only statistics/readiness/breakdown; no current-rule recomposition. |
| `supplier_offers.py` (150) | EWII product catalogue scraping/quotes create unnecessary private-contract decisions. |
| `tariff_source.py` (168) | Keep verified Radius identity/DST/dated bands/cache. |
| `update.py` (112) | One duplicate per-site release entity; HACS already owns integration updates. |
| `verification.py` (83) | No runtime caller; test-only preview pipeline and duplicate coverage resolver are dead product code. |

## Dead/duplicate paths verified by references

- `verification.verify_site`/`PreviewEngine` has only historical tests as callers, no runtime import. Retire it with its obsolete tests.
- `PriceEngine.planning` and `price_keys` are assigned but have no PE caller; `retention_days` rejects every supplied value and has no working retention feature. Retire that scaffolding; keep history without automatic pruning.
- `prices.all_in` and `price_engine.calculate` contain flat/dated/all-in branches. MVP has one dated ex-VAT official-source calculation.
- Three component/readiness presentation stacks (`component_status`, `charging_diagnostics`, `device_diagnostics`) plus canonical/display sensors duplicate card/diagnostic work.
- Legacy source modes, monthly rules, annual household eligibility, catalogue scraping, provisional estimates and HACS repair/version entities are not required to price verified EV charging quarters.

## Storage and statistics decision

No Recorder-derived daily prices. A full local-day schedule with genuinely applicable verified component rates gives immediate full-day mean/min/max across92/96/100 slots, including past and future. Newly confirmed from-now private rates must not retroactively verify earlier hours: store an explicit per-rule effective boundary. Without complete verified historical coverage use a contiguous verified remaining-day range with clearly different labels and counts; otherwise give an actionable unavailable explanation. Price records retain actual calculation/verification time, not invented historical settlement. No composition/fetch/SQL write on read.

Retain SQLite compressed content-addressed blobs, atomic incremental commits, checksums, revisions, backup/recovery. Remove the old JSON import path; schema4 uses a fresh entry-owned ledger after explicit development reset. Default entry removal retains price files; permanent selected-site reset is explicit and exact-prefix scoped. Never purge global Recorder or another site.

## API and CM decision

Replace v1 compatibility aliases/serializer with APIv2: discover sites; retrieve an immutable complete verified quarter-hour range with site, aligned slots, canonical DKK/kWh, currency, status/counts, revision/source verification and reason. Failed/incomplete/stale ranges must not expose usable unverified prices. Keep exact revision retrieval if measured EV cost recovery requires it. CM owns energy allocation/planning/control; PE owns all price calculation. Retire frozen historical CM suite gates that assert v1; add explicit v2 consumer-contract tests and a precise unreleased-CM adapter handoff. Do not claim CM runtime compatibility unless its actual adapter is updated and tested.

## Frontend, dependencies, tests and documentation

- Keep the bundled dependency-free Lovelace card: two graphs, today network bands, all quarters, selected 8-part breakdown, source/readiness. Auto-discover one readable site; provide a site selector when ambiguous. No technical entity ID needed.
- Necessary runtime dependencies: Home Assistant core (including official Nord Pool/http/WebSocket/voluptuous), Python standard library SQLite/zlib/Decimal/zoneinfo. No extra runtime packages, HACS Python imports, catalogue parser, chart plugin or CDN.
- Retain core arithmetic/Radius/verification/DST/ledger/recovery tests. Replace historical beta-specific flow/sensor/API alias tests with focused MVP config/options/sensors/statistics/API/reset/dashboard tests. Test both supported locked HA cores and actual installed packages/HACS source-tag lifecycle.
- Remove stale active guides, old demo media and obsolete publication/catalogue workflows; historical tags/Git history and immutable publication receipts preserve evidence. Update current README/setup/API/CM handoff/YAML/acceptance/performance docs to the actual MVP.

## Implementation order

1. Commit this inventory and active permanent handoff before runtime edits.
2. Simplify source/config/calculation/update boundary and introduce the compact v2 range contract; validate arithmetic/source/persistence/read invariants.
3. Replace native flow/sensors/status/statistics; remove retired modules/config/tests rather than hiding entities.
4. Simplify/discover card, complete reset and consumer handoff, native EN/DA desktop/mobile/restart evidence and before/after measurements.
5. Full relevant CI/hassfest/HACS/reproducible clean packages, guarded breaking beta10 prerelease and independent public verification. Main/stable/production/physical controls stay untouched.

## Implemented core checkpoint — beta.10

The inventory preceded changes (commit `dd4a855`). The runtime now has **22 Python
modules / 3,221 lines**, **203,492 runtime bytes**, **44,671 strings/translation
bytes** and **9 registered sensors, no PE update entity** per site. These are
working-tree measurements before final UI corrections, not a final release receipt.
Beta.9 had 37 / 7,214 lines, 876,821 bytes, 546,588 translation bytes and 40+1 entities.

Retired modules: `adapters`, `sources` (official functions merged into `prices`),
`charging_diagnostics`, `component_status`, `contracts`, `device_diagnostics`,
`estimates`, `flow_tools`, `hacs_channel`, `presentation`, `simple_setup`,
`supplier_offers`, `update`, `verification`, `repairs`. Removed monthly charges,
heating eligibility, source-entity/all-in modes, provisional estimates, display
unit aliases, old migration/preview paths and technical entity opt-out controls.
The existing compressed SQLite ledger is retained. Historical release receipts
remain immutable; earlier tagged source preserves retired code and tests.

New site schema version 4 deliberately rejects versions 1–3 without deleting data.
Reset is explicit and scoped to the selected entry. API v2 deliberately rejects
API v1; unreleased CM requires the documented consumer update before coupling.
Native accepted-step persistence reuses the official source cache on reload.
From-now rates carry a UTC quarter boundary; a separate explicit confirmation
allows the user to verify earlier quarters of today. Full/remaining/unavailable
statistics come from the schedule, with coverage counts, not Recorder samples.

Core checkpoint evidence: 99 tests on HA2026.10.3 (86% coverage), 17 locked Chromium
card tests, official hassfest 1 valid / 0 invalid, actual pinned HACS stable/upstream
add/beta visibility/upgrade from beta.9/reinstall/uninstall, and HACS-layout native
installation outside the checkout. Additional cost/statistics cases pass separately.
Current-core full run, manual package check, native UI screenshots, documentation,
consumer handoff, remote CI and publication remain pending at this checkpoint.

## Final beta.10 surface

| Measure | Published beta.9 | Beta.10 candidate | Reduction |
|---|---:|---:|---:|
|Registered entities/site|40 sensors +1 update|9 sensors|78%|
|Runtime Python modules|37|22|41%|
|Runtime Python lines|7,214|3,226|55%|
|Runtime bytes|876,821|204,206|77%|
|Strings/translations bytes|546,588|44,807|92%|

[Exact after inventory](contracts/beta10-inventory.json) records all nine IDs, units,
defaults and Recorder measurement classes. Current spot/final/DSO are measurements;
next-quarter/statistic values are schedule views without measurement state classes.
There are no hidden/deactivated compatibility entities created by new sites.
Older HA registry entries disappear only when their selected site is explicitly
reset/deleted; installing code alone does not silently delete registry history.

| Behavior | Before | After |
|---|---|---|
|Ordinary setup|Source, several saved menus, offers/estimates/technical controls|Saved source → confirmed grid → actual supplier markup → review|
|Prices|Duplicate flat/all-in/dated/provisional paths|One dated marginal formula, verified final records|
|Statistics|Full-day history gap left ordinary statistics unknown|Immediate verified full-day, or labeled contiguous remaining-day with coverage|
|Inspection|Separate canonical/display/component diagnostics|One availability attribute snapshot and card component inspector|
|Dashboard|Entity ID configuration|Automatic single site or named site selector; optional exact site ID|
|Consumers|API1 records/normalization/entry aliases|API2 immutable complete ranges, units/verification/revisions; no quotes when nonREADY|
|Storage|Compressed atomic SQLite + legacy import/planning objects|Same SQLite implementation; retired importer/planning aliases; bounded operational masks|
|Development reset|Archive/menu compatibility paths|Explicit typed selected-site reset, durable intent, fail-closed before unload|

Validation:112 producer/consumer-contract tests per supported/current HA core,
90%coverage;17 locked browser cases;actual HACS2.0.5/upstream beta9 file upgrade and
reinstall;both clean ZIP layouts outside source;official hassfest/HACS gates.
21 native HA screenshots cover EN/DA desktop/mobile, nine entities, completed and
interrupted setup, wrong input, full-day/remaining-day statistics, multiple sites,
component/tariff/quarter tables, wrong reset name and selected-site deletion.
Two actual native ledgers survived restart byte-for-byte; the reset of the second
site left the first ledger bytes unchanged. Provider counters did not change on
reads. [Recorded/synthetic evidence](receipts/v0.1.0-beta.10-simulation.json) explicitly
excludes owner HA/hardware acceptance. CM source remains unchanged and requires the
[precise API2 handoff](INTEROPERABILITY.md). Final remote source/publication evidence
is recorded in the permanent handoff and publication receipt.
