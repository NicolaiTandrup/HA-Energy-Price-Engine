# Development handoff

Updated 2026-10-27 (Europe/Copenhagen). **Beta.6 active**, explicitly authorized by
new owner mission after beta.5 acceptance feedback. Branch `feat/beta6-marginal-pricing`
continues final beta.5 checkpoint **a7a6b04**; all10 prior handoff CI jobs verified
successful. Main/prior tags/releases remain unchanged. No worktree, production HA,
Node-RED, Tesla/Easee/CM controls, stable release or main merge. Owner authorizes
beta.6 prerelease only after mandatory gates; stop after publication/verification.

## Beta.6 fractional markup and three-step foundation

Checkpoint subject: **feat: accept fractional charging markup in three-step setup**.
Issues#8/#12 read including final owner scope corrections: marginal per-quarter
charging prices, not household invoice reconstruction. Issue#10 graphs deferred.

- Source → confirmed grid product → actual fractional supplier markup → Review.
  Ordinary form has markup and VAT basis only: no product/monthly subscription,
  dates, heating eligibility or technical source contract. Public national defaults
  stay bounded to verified periods; no private rates/eligibility inferred.
- Text-based decimal input deliberately accepts point/comma across browser locales;
  decimal parsing rejects ambiguous/nonfinite/negative values, persists exact decimal
  strings and converts ore to numeric DKK through Decimal. Canonical pricing/VAT
  composition/API remain unchanged. Source/grid shape, SQLite and refresh engine
  retained. Existing subscriptions/future overrides/history preserved.
- Server-resolved menu dictionaries ensure nonempty human labels independent of
  client translation cache. Fresh beta.5 en/en-GB/da resources all resolve correctly;
  owner log references older draft_status wording. Add explicit compatibility
  placeholder and complete en-GB resources; actual frontend cache-path checks pending.
  Official advanced source schema hides entity-only fields and validates source,
  area/timezone with field-specific errors while retaining entered data.
- Focused new fractional native flows, real HA translation resolution and current
  contract regression **32 passed**. Core/contract/locale foundation18 passed. Ruff
  check/format pass. Full older flow tests still require navigation adaptation;
  no full-suite/remote green claim for this changed checkpoint.
- Local GitHub API remains proxy-blocked; public GitHub web/Git work. Initial
  authorized GitHub runner opens a draft beta.6 PR; publication later uses the
  proven immutable source/hash gates and independent public verification. No beta.6
  tag/release yet. Manifest still beta.5 during this in-progress foundation.

Next: adapt/re-run existing flow/package regression; canonical stored current/future
component diagnostics, allocated-energy read-only charging cost estimate, real Radius
TOU/midnight/DST/fractional tests, beta.5 source migration, native EN/en-GB/DA mobile/
desktop evidence, full both-core/consumer/SQLite/HACS/hassfest/package/CI gates, clean
source/tag and authorized beta.6 prerelease, public verification and final stop handoff.
Only this document is the permanent handoff. Owner real-HA acceptance remains false.

## Earlier beta.5 handoff (historical)

## Completed beta.5 publication

https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases/tag/v0.1.0-beta.5

- Immutable release source **a4ede923e42573def49026a8d1d817c37a979171**.
- Annotated tag **7a919061010e1a018a54235e96711ff4295622a7**.
- Branch **feat/beta5-simple-onboarding**, draft **PR #14**, unmerged.
- Main remains **56cdb3c10993179371483812cbc36f651ba3ad8e**; prior releases/tags/assets
  preserved. No stable release, live HA, Node-RED, CM, vehicle or charger changes.
- All **15 exact-source push/PR/tag jobs green** before publication. Producer
  **234 passed/core**, HA 2026.10.3/current 2026.10.4, 88% coverage, zero skips. Two
  pinned upstream HACS deprecation warnings. Current stable .4 independently checked.
- Unchanged consumer suites **153/176/227/228 per core**, two actual coupled runtime
  startup-order/revision/unload cases per reference/core. No consumer code rewritten.
- Official hassfest one integration/zero invalid, HACS validation/translations,
  clean deterministic archives and both layouts independently installed outside
  source on both cores. Original transactional SQLite touched-row performance retained.
- Publisher **40559712967**, orchestration ec2ad995f2d5b59b5ee031daf2a68f1db7d859b9,
  verifies exact annotated object/source, all 15 green checks, expected ZIP hashes,
  clean rebuild and both native installs before prerelease/latest=false upload.
- Two fresh independent postpublication core jobs downloaded public API metadata,
  four assets, immutable tag source and compliant public main. Actual unchanged
  pinned HACS 2.0.5/upstream add/discover/tag install/update/uninstall/reinstall and
  both native ZIP layouts passed. Public semantic feed selects beta.5 for beta.4,
  stays current for installed beta.5 and excludes beta/hashes for stable users.
- Local unauthenticated public page HTTP 200/prerelease badge, all four downloaded
  assets and their digests, every runtime file against public tag/local exact source,
  annotated/peeled remote tag, main/prior beta.4 preservation independently checked.
  Downloaded root/manual ZIPs each passed native outside-source installs on both
  cores. Local actual HACS replay using independently downloaded public tag/main
  bytes and runner-captured public metadata also passed 2 cases/core. Local public API CONNECT403 after cloud reconnect was handled by authorized
  runner API checks; no credential replacement/proxy or integrity bypass.
- Publication receipt **docs/receipts/v0.1.0-beta.5.json** includes exact check/job/
  release/asset metadata and both public verification receipts. Native simulation:
  **docs/receipts/v0.1.0-beta.5-simulation.json**. Illustrated guide, 19 screenshots and
  two short EN custom/DA EWII demonstrations in docs/WIZARD_GUIDE.md.
- Final checkpoint subject: **docs: finalize verified beta.5 publication and stop handoff**.

SHA256:
- ha_energy_price_engine.zip: 9f8ea839a04b5d67f61dc0e49f11611abcb4c85cdfced809f813937548dc0ad0
- ha_energy_price_engine-manual.zip: 422c5d1bb39c4596a4af36db2e325ad56b642b8287e2bc09409d96a5928d3036

## Result and remaining owner acceptance

Five ordinary native stages save every accepted page in actual config. Saved
confirmation and Configure resume replace hidden draft/final-save flows. Source
facts establish conventions/area; Radius C needs actual product confirmation.
EWII Basis/Plus are fresh official public suggestions only, with 24h maximum fallback.
Their markup VAT convention is not established by official pages, so confirm it
from the actual agreement. Custom input is ore/kWh/VAT/optional monthly fee with no
ordinary dates. Standing terms start next complete quarter, no earlier unknown
backfill or settled rewrite; future scheduled date/hour overrides remain. Monthly
fees stay outside marginal prices. Numerical review has eight direct component
settings and one Check prices; details/dated editing/storage live under Diagnostics.
Raw vs final readiness stays distinct; estimates never give ledger/API READY.

Real native EN/DA desktop/mobile journeys passed: custom/public agreement, accepted
step persistence and interrupted resume, direct corrections, missing/provisional,
source outage/recovery and explicit verification. Mobile document width 390 with no
horizontal overflow or frontend errors. Four beta.4 sites preserve config/source/
identity/history. Nine-site restart preserves settled SQL rows/revisions. Confirmed
selected 115-row deletion removes only that entry/setup; same-name recreation has
new ID/empty history. Other sites/global recorder retained. Synthetic software
checks are not owner acceptance. QA server stopped after evidence collection.

No prerelease-publication blocker remains. Owner acceptance stays unchecked:
HACS Show beta versions → refresh → select v0.1.0-beta.5 → download → restart;
Device info version 0.1.0-beta.5; Configure existing site (do not delete/recreate).
Confirm own bill/agreement/VAT/grid class and public-source timing, verify restart
and 13:05/13:20/13:40/23:59/00:01 schedules, actual mobile usability and hardware.
Ordinary automatic setup targets Danish DK1/DK2/Radius C; other grid products and
future periods require verified advanced rules. National defaults are bounded 2026
Energinet and .008 tax 2026–27 baselines, not live legislation discovery. Heating
eligibility is never guessed. New sites can have partial first-day final coverage;
full-day API still requires every quarter. Native Close cannot submit typing;
avoid simultaneous edits of one site. Existing entity language follows HA registry/
system settings; forms follow the user's language. HACS external catalog branding
can fall back while native PE icon works. Two-price-chart issue #10 remains separate.

SQLite cloud repeat: 35,136 rows, 18,239,488 bytes; append 96 rows .0457s, reload 2.240s,
lookup 10.06us, peak 243,448KiB under concurrent validation. **Cloud timings do not
establish Raspberry Pi performance.** Immutable history stays in RAM for API v1;
measure actual hardware and recovery. No live-source/bill/hardware/owner acceptance
or production cutover is implied. Follow docs/BETA_ACCEPTANCE.md.

## Earlier beta.5 development checkpoints (historical)

## Beta.5 initial checkpoint

Checkpoint subject: **ci: investigate authoritative EWII product terms for beta.5**.
Direct cloud requests to official EWII URLs fail at network proxy (403 tunnel).
Read-only GitHub-runner verification records official source URL, retrieval time,
HTML hash and relevant rate/VAT/subscription text as check notices. Never convert
owner-provided illustrative offers into verified current presets without evidence.

Implementation plan: five ordinary stages, step-confirmed ConfigEntry persistence,
no final draft commit, rate-from-now/open-ended confirmed supplier terms, concise
rate/source/status checklist and direct corrective settings. Public offers require
explicit agreement confirmation; custom markup/VAT/monthly optional. Monthly fees
remain outside marginal prices. Preserve advanced dated rules, consumer API, ledger,
source adapters, safe deletion and mandatory refresh times. Activation must not
backfill earlier unverified intervals. New UI must be tested in real disposable
HA frontend EN/DA desktop/mobile, including close/reopen and beta.4 migration.

Foundation checkpoint: **feat: accept current supplier rates without backfilling history**.
35 focused contract/pricing/schedule/readiness tests passed. Current contract terms
start at the next complete UTC quarter, use an open-ended end date, preserve prior
settled ledger rows and never fill earlier unknown intervals. Monthly subscription
remains separate; provisional rates stay outside verified ledger/API. Additive
verified-range metadata lets the existing read-only API certify complete requested
future ranges while full-day reads remain INCOMPLETE for new partial first days.
SQLite touched-row persistence/arithmetic are unchanged. Setup progress is owned
storage and included in selected-site cleanup.

Official runner reads succeeded; primary markup/monthly quotes observed at EWII.
VAT conventions still require authoritative verification before offering automatic
rates; do not guess from consumer-page appearance. Source capture bounded notices
being refined because GitHub limits annotations. No beta.5 tag/release yet.
Next: verify authoritative product sources,
implement/test incremental saving and current-rate activation, then simple native
setup/diagnostics, full regression/consumer/HACS/package/CI gates and actual frontend
journey screenshots/demonstration before immutable prerelease publication.


## Beta.5 native saved-step checkpoint

Checkpoint subject: **feat: replace draft onboarding with saved native setup and rate checklist**.
PR **#14**; latest prior committed foundation032a502. No beta.5 publication or owner acceptance claimed.

- Five ordinary stages. First source confirmation creates the actual entry; each
  accepted page writes actual ConfigEntry options and updates pricing. Native HA
  post-create FORM continuation keeps the same stable site ID. Closing resumes
  saved progress; review needs no final commit or incomplete-finish form.
- Source area/timezone/unit inferred only from official source facts. Radius C
  requires explicit actual-product confirmation; other rates accept current values.
- Named EWII suggestions fetched/parsed from official pages, with URL/time/HTML
  digest and a strictly24h fallback snapshot. Basis16.5øre/0monthly and Plus6.5øre/
  29monthly independently retrieved by runner40550840062. Product pages/general
  pages do NOT state a reliable markup VAT convention: it remains null and the
  user must explicitly select the actual VAT basis before confirming agreement.
  No campaign/historical/private terms inferred. Public rates are suggestions only.
- Custom markup is øre/kWh, optional monthly subscription and VAT, no dates. Current
  agreement confirmation or explicit visualization-only estimate; open-ended until
  changed, no earlier unknown intervals backfilled. Advanced dated edits retained
  and now applied on acceptance too. Old unpublished beta.4 drafts are not silently
  activated. Existing active entries/rates/history remain authoritative.
- Compact native component checklist: numerical rate/source/status, each row opens
  its relevant settings; one Check prices action. Advanced details behind final
  price/Diagnostics. Review rates include VAT; structured diagnostics retain explicit
  canonical ex-/incl-VAT values. Download diagnostics redact private free-form sources.
- Step changes reuse only the existing verified Nord Pool cache with original
  timestamp/error/backoff; explicit recheck and mandatory schedules still force
  verification. Config reload failure marks consumers STALE before retry, never
  certifies previous READY prices for newly changed settings. SQLite engine writes
  and persistence remain unchanged.
- Local focused gates: foundation35; UI/core24; migrated flow regression50; remaining
  compatibility20 passed. Initial full run225 passed/5 obsolete navigation failures;
  those tests migrated without dropping underlying identity/source/history checks.
  Full second suite: **230 passed**, two upstream HACS warnings. Current-core repeats pending. Root ZIP independent native
  installation1 passed; manual layout/remote gates still pending.
- Actual HA .4/frontend20260930.5 EN desktop/mobile first run passed, including
  close after supplier acceptance and Configure resuming tax. New site has source96,
  remaining-day verified21/96, tomorrow96/96; future confirmed price.6675 DKK with
  fictional.111exVAT supplier, no past backfill. Native start-time explanation.
  Width390=document390; final console errors0. System ffmpeg used for requested
  recording because Playwright CDN encoder download was blocked. Only non-PE
  decorative branding mocked; native PE icon served normally. Old draft wizard implementation removed after replacement tests passed; management
  actions reused unchanged in flow_tools.py. Final UI refresh/DA/product/missing/
  provisional/restart/delete journeys still required.

Next: complete local full gates; commit/push this checkpoint, then final native
frontend evidence/demo, concise public docs, current-core/consumer/HACS/hassfest/
package/migration/SQLite checks, clean source and exact-source CI before beta.5 tag
and authorized immutable prerelease publication. No beta.5 tag/assets/release yet.


## Beta.5 current-rate refinement

Checkpoint subject: **fix: preserve scheduled overrides when accepting current terms**.
Known native implementation **8b52444**. Both full local core suites **230 passed**,
87% coverage, zero skips, two upstream HACS warnings; all **10** push/PR checks at
8b52444 green (full unchanged consumers/runtimes, metadata and independent packages).
Local hassfest0 invalid. Final ordinary review/diagnostics basis is explicitly
including VAT; canonical component diagnostics retain ex-VAT applied values too.

Current-rate confirmation now retains existing future supplier/grid/subscription
schedules and fills only uncovered date/hour ranges with the new standing rate.
Old settled history remains untouched. Focused contract/new-flow/advanced/migration
suite **33 passed**. Same-site unique active private markup can be prefilled when
editing; no expired/other-site/private rates discovered or guessed. Final full
matrix must be rerun after refinements; final native DA/public product/diagnostic/
missing/provisional/restart/reset evidence and docs/publication remain pending.
No beta.5 tag/release/publication yet.


Source-step refinement: **fix: save ambiguous source areas in the first accepted step**.
Source area is requested on the first page only when installed source metadata is
ambiguous; no intermediate accepted-but-unpersisted source page. No DK2 guessing.
Same-source unique area is automatic. Focused source/current/old-version flow gate
**36 passed**. Prior current-rate refinement c08620d retained future schedules.
Final runtime/UI refresh and remaining release gates continue; no tag/release yet.

## Earlier beta.4 handoff (historical)

## Completed beta.4 publication

Public prerelease:
https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases/tag/v0.1.0-beta.4

- Exact source **38973d88ad67758b419dfc45c193a8c85674afda**.
- Immutable annotated tag **90cb819f001fd390ca35e1c83f26d3c6303c4de1**.
- Branch **feat/beta4-complete-pricing**, draft **PR #13**, unmerged.
- Main remains **56cdb3c10993179371483812cbc36f651ba3ad8e** (beta.1).
  Beta.1–.3 tags/releases/assets preserved; beta.3 tag remains 73b9e9e48d4cb17c69ecff4f77d9c992a5307516.
- All **15 exact-source push/PR/tag checks green** before upload. **221 producer
  tests per HA 2026.10.3 / current 2026.10.4**, 88% coverage, zero skips, two pinned
  upstream HACS deprecation warnings. PyPI latest .4 independently rechecked.
- Full unchanged consumer suites **153/176/227/228 per core**, two actual coupled
  runtime/startup-order cases per consumer per core. No consumer code rewritten.
- HACS registration/install/update/uninstall/reinstall uses unchanged pinned stable
  2.0.5/upstream code. PE-only beta repair traverses authenticated local HTTP/
  WebSocket commands, actual HACS store write AND restore; semantic update values.
- Official hassfest **one integration, zero invalid**, HACS metadata/translations,
  deterministic clean packaging and independent installs of BOTH layouts passed.
- Publisher **40543649671**, orchestration source a18e2a45d6744d4851bf8c4ec6b52b6aa977daf8,
  succeeded. It rebuilt immutable source, checked tag object and exact ZIP digests,
  awaited all 15 source checks and installed both layouts before prerelease/latest=false.
- Public release **425732368**, non-draft prerelease, unauthenticated page HTTP200.
  Public main/tag/source and all FOUR assets independently downloaded and verified
  on BOTH cores: digests, source/file payload, manifest/clean commit match. Actual
  public HACS plus root/manual native imports/install/reload/remove/recreate passed.
- Actual public release feed chooses beta.4 for beta.3, stays beta.4 when installed,
  excludes prereleases and hashes for stable users.
- Permanent receipt: **docs/receipts/v0.1.0-beta.4.json**.
  Final checkpoint subject: **docs: record verified beta.4 publication and permanent handoff**.

SHA256:
- ha_energy_price_engine.zip: 8204ef21583927b0973d59becf33f66575618cde755371989ef835e5af183d58
- ha_energy_price_engine-manual.zip: 1a2f196dde01f1a92c6dab3221d9306d45171688803a3ca22d1794ad869ae491

## Functional acceptance evidence and limits

Direct blank supplier markup in øre/kWh, bill/contract VAT/date guidance, explicit
verification and separately approved provisional visualization. Missing amounts
never become zero. Estimates reuse canonical calculation transiently, never enter
verified ledger/revisions/API READY, and must never control charging.

Native compact Today/Tomorrow table has direct missing corrections and one Save;
actual reload/persistence is awaited. Incomplete/failed persistence returns a
saved-incomplete corrective form, never success based on stale/preflight results.
Archive removal identifies retained history; confirmed permanent selected-entry
cleanup quiesces writers, clears exact-owned configuration/SQLite/backups/drafts/
registries and blocks interrupted restart. Other sites/global recorder preserved.

Real disposable HA .4/frontend 20260930.5 EN/DA desktop/mobile complete/missing/
provisional journeys, invalid verification, interrupted resume, wrong deletion
confirmation and actual 192-row permanent deletion/recreation passed. Fixed a
browser-discovered selection reset after error; destructive choice/typed ID now
persist. Native PE branding served without PE image substitution. Final console
errors 0, viewport 390 = document 390. Source .100 DKK/kWh plus synthetic .200 grid,
FICTIONAL .111 supplier, bounded .043/.072/.008 national rates and 25%VAT produce
.6675 DKK/kWh (66.75øre). Do not copy fictional private rates.

Full restart preserves every decoded row/amount/provenance/revision in four
verified ledgers; provisional ledger remains absent, raw READY 96, estimate.6675,
authoritative INCOMPLETE. Beta.3 inherited past rows unchanged; actual immutable
beta.1/.2/.3 source migration fixtures pass. Negative prices and 92/96/100 DST
quarters, missing/expired rates, SQLite failure/recovery/migration and historical
revisions covered. Required 13:05/13:20/13:40/23:59/00:01 schedule preserved.
Evidence **docs/receipts/v0.1.0-beta.4-simulation.json**, **docs/images/beta4/**.

One-year cloud SQLite repeat 35,136 rows: append 96 .0293s, reload .891s, lookup 6.65µs,
18,239,488bytes. **Cloud benchmarks do not establish Raspberry Pi performance**.
History remains in memory without silent pruning; measure target hardware.

No software publication blocker remains. Owner installation/current contract,
public source/bill and hardware acceptance remain UNCHECKED. Public national
baselines are dated, not live legislation; later periods/other grid products need
verified rates. Private contracts/heating eligibility are never guessed. Native HA
Close cannot submit keystrokes: Continue first. Entity names follow system language/
registry; forms/selectors/new enums follow the current user language. HACS's own
external brands CDN may use a fallback pending separate catalog review; supported
bundled HA/README/PE update branding works. No global HACS patch ships.

## Exact owner update/retest

HACS → Energy Price Engine → persist **Show beta versions** → refresh → select
**v0.1.0-beta.4** → download → restart. Existing site **Configure**, not Delete/Add.
Device info must show 0.1.0-beta.4. Follow six stages with your actual supplier
markup/unit/VAT/effective dates; Review and Save & verify. Inspect raw/final coverage,
one stored breakdown, restart and compare to invoice. If HACS latest is a hash,
Advanced → Repair HACS beta channel (explicit admin approval) or HACS's own beta
visibility control. The action installs nothing. Guides: WIZARD_GUIDE.md,
HACS_DISTRIBUTION.md, BETA_SETUP.md and BETA_ACCEPTANCE.md. All are public and neutral.

## Earlier beta.4 checkpoints (historical, before completed publication)

## Beta.4 checkpoint

Checkpoint subject: **feat: add explicit supplier estimates and persisted setup verification**.
Based on beta.3 final handoff 4560ec6; draft PR #13.

- Direct supplier markup defaults to øre/kWh, blank amount, explicit bill/contract
  verification; optional separately approved provisional amounts. Existing periods
  retain their identities; explicit replacement splits overlaps without losing
  unrelated dates. Historical EWII is never a current preset.
- Provisional calculation reuses the canonical calculator in transient memory.
  Dedicated ESTIMATED/UNVERIFIED sensors cannot enter ledger/API READY or revisions.
  Real runtime tests cover normal/92/100 quarters and restart isolation.
- Compact native translated Today/Tomorrow comparison with conditional correction
  choices. Advanced holds manual edits, diagnostic steps and draft discard.
- Save awaits exactly one normal reload/persistence; initial HA post-create hook
  and Options return a corrective saved-incomplete form until actual runtime/API
  has complete verified current-day prices. Tomorrow publication remains separate.
- Default removal records identified archives and clears stale entry/initial
  drafts. Explicit confirmed permanent removal quiesces schedule/writers before
  deleting exact-owned files; durable ID-only intent blocks interrupted restart.
  Tested second-site/recorder/symlink isolation and clean same-name recreation.
- PE-only HACS channel repair uses its supported authenticated local WebSocket
  commands with explicit user approval. No HACS patch, global settings change,
  package installation or remote credential forwarding. Both pinned HACS lines
  passed native authenticated HTTP/WebSocket repair, actual HACS store persistence,
  semantic UpdateEntity values and tag download/update/uninstall/reinstall tests.

Second checkpoint subject: **fix: complete beta.4 review reporting and public setup guides**.
Known implementation commit e95152d pushed; PR #13 stays draft/unmerged.

- Full producer run before final edge fixes: **213 passed** on HA .4 (88% coverage),
  **211 passed** on .3 before two newly added direct-flow cases. Zero skips; two
  upstream HACS warnings. Complete final runs remain required.
- Four unchanged consumer full suites on current core: **153/176/227/228 passed**;
  actual coupled-runtime tests **2 passed per consumer**. Supported-core repeats pending.
- Official local hassfest: **1 integration, zero invalid**. Both ZIP layouts built
  dirty for development and independently installed outside source: **1 passed each**.
- Native actual frontend EN complete, missing supplier and provisional journeys
  passed without console errors using synthetic source/Radius. Complete setup 96
  raw/final quarters each day; incomplete/provisional saved forms show no success.
  Browser exposed lost grid_status after save; now retained in durable day report.
- Final edge gate **16 passed**, including failed-save rejection of old READY
  runtime, concurrent deletion intents, direct øre markup verification and native
  destructive confirmation. New regression fixture includes actual beta.3 source.
- Public README and four setup guides rewritten without private hostnames/internal
  PR details; contributor documentation separate and public-doc lint added.
- Beta.4 manifest/version/package verification targets updated. Local HA native
  brand renders with no PE image substitution; HACS external CDN fallback explicitly
  documented. No unsupported HACS/HA frontend patch ships.
- Repeated one-year SQLite benchmark: 35,136 rows, 18,239,488 bytes; append 96 .0293s,
  reload .891s, mean lookup 6.65us. Cloud x86_64, explicitly not Pi performance.

CI on first e95152d checkpoint correctly failed stale schedule/review tests now fixed;
HACS/hassfest/independent install CI passed. One supported-core job failed dependency
preparation before tests. Do not report initial CI green. Next push reruns all gates.

Next: final source tests/core matrix and unchanged consumers, disposable native DA/
mobile/restart/delete/recreate checks and screenshots; clean packages and CI; only
then immutable source/tag and authorized beta.4 publication/integrity verification.
No beta.4 tag/release/assets have been published. Owner acceptance remains pending.

Third checkpoint subject: **fix: retain destructive form choices and fetch beta.3 migration source**.
Known second checkpoint 9512a77. Both full local suites now **217 passed**, 88%
coverage, zero skips, two upstream HACS warnings. Four unchanged consumer suites
153/176/227/228 and paired runtime cases2 each passed on BOTH HA cores. Both ZIP
layouts passed independent imports/install on both cores; local hassfest0 invalid.
Native DA desktop/mobile table follows user language with system EN; mobile width
390=document390, no console errors. Verified synthetic all-in .6675 DKK/kWh.

CI failure at 9512a77 precisely diagnosed via check annotations: shallow checkout
lacks the newly added immutable beta.3 migration source; preparer fetched only
beta.1/.2. Added beta.3 source to the same preparer (no weakening of migration test).

Actual mobile reset exposed operation resetting to archive after confirmation
error. It safely archived the disposable provisional entry but violated selected
intent. Preserve operation/typed ID/confirmation on validation errors; native test
asserts retained defaults. Five focused tests passed, including actual HACS store
restore with semantic version values after restart. Native destructive retest with
an actual ledger and fresh recreation is in progress. Final CI/screenshots/release
integrity remain pending. No beta.4 publication yet.


Fourth checkpoint subject: **test: record beta.4 native acceptance simulations and deterministic HACS fixture**.
Known implementation commit **4e98db6cb0782be2131ce40ca30ad8e049c5c8df**.
Final runtime source unchanged from that commit; next changes are tests/docs only.
Actual release source is not yet selected/tagged.

- Both final local producer suites: **217 passed**, 88%, zero skips, two upstream
  HACS warnings. Added four further credential-boundary cases (non-admin/public/
  wildcard/multicast socket rejected before any network); focused both-core gate **9 passed each** (two HACS warnings).
- Both-core unchanged consumer and runtime suites passed; clean independent ZIP
  installs passed on both. Local hassfest0 invalid, remote HACS/hassfest/package green.
- Real frontend EN/DA desktop/mobile complete/missing/provisional journeys, invalid
  supplier approval, interrupted/resumed draft and actual destructive confirmation
  tested. Corrected operation remains permanent after wrong ID error; final mobile
  deletion removed an actual 192-row ledger and its config/drafts/registries.
  Same-name fresh creation has new entry ID and no old accounting references.
- Native final screens no page/console errors, mobile390=document390, systemEN/userDA
  translation verified. Native PE branding loaded without PE image mocks.
- Restart preserved all four verified ledgers' complete decoded SQL rows/checksums;
  provisional site's ledger absent, raw.100, visualization.6675, authoritative
  readiness INCOMPLETE. Beta.3 inherited past rows unchanged. Evidence:
  docs/receipts/v0.1.0-beta.4-simulation.json and docs/images/beta4/.
- CI4e98 current-core push passed full job; supported-core push exposed test-only
  race registering HTTP view after test client freezes router. Fixed registration
  ordering (view/commands before client); real HACS code unchanged. Both PR matrix
  jobs in progress at checkpoint. Do not publish until exact-source all green.

Next: finish focused both-core checks, push evidence/test fixture checkpoint, await
all mandatory source checks. Then build immutable clean source, tag/package hashes,
authorized prerelease publisher and independent public install/source verification.
Owner acceptance remains unchecked; HACS external CDN icon requires separate catalog
review, bundled native HA/README/PE update branding works. National baselines are dated,
not live legislation. Continue before closing unsent forms; HA entity naming uses
system/registry language. No stable/main/live/control changes.


## Beta.4 publication orchestration

Authorized source **38973d88ad67758b419dfc45c193a8c85674afda**; immutable annotated
v0.1.0-beta.4 tag object **90cb819f001fd390ca35e1c83f26d3c6303c4de1**. All **10** push/PR exact-source
checks green before tagging. Final producer **221 passed per core**, 88% coverage,
zero skips, two upstream HACS warnings. Current PyPI rechecked **2026.10.4**.
Both final clean archive layouts independently installed on both cores.

Fixed-source publisher rebuilds that tag, checks annotated tag identity and exact
ZIP digests, requires all **15** source checks (push/PR/tag) green, independently
installs both layouts and only then publishes prerelease/latest=false. Orchestration
commit is separate from release source. Publication/post-public verification pending.
SHA256 root: 8204ef21583927b0973d59becf33f66575618cde755371989ef835e5af183d58
SHA256 manual: 1a2f196dde01f1a92c6dab3221d9306d45171688803a3ca22d1794ad869ae491

Next: monitor publisher/tag CI, independently download public metadata/tag/main/all
four assets, compare source/payload/hashes, run actual HACS and both native installs
on BOTH HA cores, record final receipt/handoff and update PR. Stop after beta.4
publication verification; no main merge or further features. Owner acceptance pending.

---

## Completed beta.3 software publication

Public prerelease:
https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases/tag/v0.1.0-beta.3

- Source: **78ef9ba4d02ccb85b9395991d1376fbdec34bb84**.
- Annotated tag: **73b9e9e48d4cb17c69ecff4f77d9c992a5307516**, never moved.
- Branch **feat/beta3-functional-onboarding**, draft **PR #11** unmerged.
- Main remains beta.1 **56cdb3c10993179371483812cbc36f651ba3ad8e**. Beta.1/.2 tags,
  releases and assets unchanged. HACS registers compliant main and installs exact tag.
- All **15 final source check runs** green: producer/unchanged consumers/coupled
  runtime orders on both HA cores, HACS, official hassfest and independent installs.
  **200 passed per HA 2026.10.3 / 2026.10.4**, 89% coverage, zero skips. Two
  upstream HACS deprecation warnings. Current PyPI core rechecked: 2026.10.4.
- Tag current-core job initially failed preparing pinned dependencies BEFORE tests.
  Supported-core tag job and all push/PR jobs passed. Failed job rerun with debug
  succeeded without source changes (run 40526919031, attempt 2). Publication guard
  correctly stopped before uploading until all source checks passed.
- Fixed-source publisher run **40527012490 attempt 2** succeeded; orchestration
  commit **13218d3**, not release source. It rebuilt immutable tag, checked exact
  ZIP hashes and both native installs, then published prerelease/latest=false.
- Actual public repository/main/tag/source and all FOUR assets independently
  downloaded and verified on BOTH HA cores. Digests, checksums, source/file payload,
  manifest/clean commit match. Unauthenticated release page HTTP200, non-draft
  prerelease. No software distribution blocker remains.
- Unchanged pinned HACS 2.0.5/upstream registration with actual main bytes, beta
  discovery, selected tag download/extraction/update/uninstall/reinstall passed on
  both cores. Both public ZIP layouts passed outside-source native wizard/Options/
  SQLite reload/delete/recreate. Actual public release metadata selects beta.3 for
  beta.2, stays beta.3 for current install, and excludes beta/commit candidates for
  stable users.
- Permanent receipt: **docs/receipts/v0.1.0-beta.3.json**.
  Final checkpoint subject: **docs: record verified beta.3 publication and retest handoff**.

SHA-256:
- ha_energy_price_engine.zip: 300741806e86d5566b6ab025f814aac1c52d21c50bc2273c3a5ff4b20387c3e9
- ha_energy_price_engine-manual.zip: 37b4af805818de1a200e34b7eb3a8c225b0624ef4003e0303485b0bf6bef8c5e

## Functional evidence and scope

Latest #8 feedback read fully. Reported generic failure path reproduced: valid
96-quarter source + verified Radius can still fail final composition when supplier/
national rules are missing. No claim of knowing the owner's private missing values.
New raw current/next and daily source readiness/coverage/timestamps remain observable
independently. Missing periods are INCOMPLETE; source/grid/storage failures have
separate corrective categories. Final verified coverage versus retained historical
rows is explicit without changing API v1 valid_slots semantics.

Review reads actual source adapters and the canonical calculate() in a transient
sink; no draft ledger writes. It shows all dated components and direct correction
steps, then Save rechecks/applies once through normal runtime persistence. No hidden
extra Save. Source validation appears on grid step. New Danish official-source sites
visibly suggest bounded national baselines, never private/grid connection inference.
Canonical eligibility predicate is shared with diagnostics; civil-hour coverage
handles spring's absent hour and verified heating evidence consistently. Arithmetic,
SQLite performance improvement and scheduled 13:05/13:20/13:40/23:59/00:01 retained.

Real disposable HA .4/frontend 20260930.5 native EN/DA new-site journeys persisted
96 raw and final quarters per day: synthetic .100 spot + .200 grid + FICTIONAL .111
supplier + .043/.072/.008 national components, 25% VAT = .6675 DKK/kWh / 66.75 øre.
Missing supplier retained raw READY 96 and final INCOMPLETE 0 with exact period.
Radius outage, source cached STALE, partial source and recovery distinguished;
ledger failure covered in actual runtime tests. Both 192-row ledgers retained
identical UTC rows/amounts/revisions across restart. Actual beta.1/.2 released source
seeds migration fixtures. Tests cover negative prices, normal/92/100 slots and
eligible-heating/spring-hour UI consistency.

Final native desktop 1440x1000 and mobile 390x844 Review/correction checks EN/DA:
no page/console errors; mobile document width=390px. User Danish/system English
verified. Browser plugin absent: regular Playwright/system Chromium. Only decorative
brand images substituted; real native HA forms/runtime. Synthetic source/Radius
boundaries, not owner credentials/live rates. Fixture rechecks after adding its
synthetic provider; actual official dependency/recovery tested separately.
Evidence: **docs/receipts/v0.1.0-beta.3-simulation.json**, **docs/images/beta3/**.

## Exact owner update/retest and remaining limitations

HACS -> Energy Price Engine -> persist **Show beta versions** -> refresh information
-> select **v0.1.0-beta.3** -> download -> restart HA. Existing site's **Configure**,
not delete/recreate. Confirm manifest-derived Device info .3; review source/grid/
supplier/national/display, Continue pages, then Save & verify. Check actual raw/final
coverage, problem/affected period and one stored breakdown. Guides:
**docs/WIZARD_GUIDE.md**, **docs/HACS_DISTRIBUTION.md**, **docs/BETA_SETUP.md** and
**docs/BETA_ACCEPTANCE.md**. Owner PAHA02-DEV source/contract/billing/Pi acceptance
remains unchecked. Isolated tests/screenshots are NOT owner acceptance.

Native HA limits are explicit: Close/reload does not submit keystrokes; Continue
first. Submitted drafts/errors/Back edits persist; avoid simultaneous flows for one
site. HA entity names follow system language/existing registry, not per-user global
renaming. Both name resources ship; wizard/validation/Repairs/new lowercase enum
messages follow user UI language. Legacy uppercase state/API contracts preserved.
Canonical technical keys and provider exception text retain original conventions.

Actual HACS short-hash root cause reproduced: show_beta false + no stable release
falls back to main commit. PE does not patch HACS; keep its beta visibility on.
hide_default_branch prevents explicit development selection. PE-owned read-only
UpdateEntity offers only published valid SemVer releases in the installed channel;
no draft/hash/update installation. GitHub metadata failure is independent of prices.

No private contract/heating eligibility invented. EWII household .030 ex-VAT fact
is June-September 2026 only. Future/other-site terms remain unknown. Public periods
bounded; automatic grid initially confirmed Radius C, others manual. Cloud results
are not Raspberry Pi evidence; all authoritative history stays in RAM, never silently
pruned. No owner/production HA, PAHA01, Node-RED, Tesla, Easee, charging commands,
main merge, stable or CM release operation. Disposable QA instance is shut down
before the final response. Stop after this handoff.

Following beta.2/beta.1 sections are historical; old next-step instructions do not
reopen their completed development missions or establish owner acceptance.

## Completed PE beta.2 — final receipt

Public **prerelease**:
https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases/tag/v0.1.0-beta.2

- Exact source: **0c93d2bfac88878cff46e7726f59accbeababf85**.
- Annotated tag object: **985ad4af194bb0b261ed73dcb22ea4d8c1bb5952**, never moved.
- Branch **feat/beta2-guided-setup**, draft **PR #9** remains unmerged/reviewable.
  Main remains beta.1 **56cdb3c10993179371483812cbc36f651ba3ad8e**. HACS registers
  from compliant main, then downloads the exact beta.2 tag. No main change was needed.
- Publisher orchestration **34cb19e** checks out the immutable tag, verifies successful
  exact-source CI, deterministic ZIP hashes and independent native installs, then
  publishes with `--prerelease --latest=false`. Actual run succeeded:
  https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/actions/runs/40467818996
- All **15 actual source checks** (push/PR/tag) passed: both-core tests, unchanged
  consumer suites/coupled runtimes, HACS, official hassfest and independent installs.
  Both local HA **2026.10.3 / 2026.10.4: 185 passed**, 88% coverage, zero skips.
  Current PyPI core rechecked: 2026.10.4. Two upstream HACS deprecation warnings.
- Independently downloaded actual public metadata, source ZIP, main ZIP and all four
  assets on BOTH cores. Tag/source/manifest/per-file payload/GitHub digests/checksums
  match. Public unauthenticated page HTTP200, non-draft prerelease confirmed.
- Unchanged pinned HACS 2.0.5/upstream methods passed registration using actual beta.1
  main bytes separately from beta.2 selected tag, beta discovery, download/extraction,
  update, uninstall/reinstall. Both public ZIP layouts passed outside-source native
  wizard setup/Options/SQLite reload/delete/recreate on both cores.
- Machine-readable evidence: **docs/receipts/v0.1.0-beta.2.json**. Final checkpoint
  subject: `docs: record independently verified beta.2 publication`.

SHA-256:

```text
968a3436d7d44f20b4e86db405dcd26b553b9baa2a81dcfbf6eb9daf70776d91  ha_energy_price_engine.zip
a53f5a2ede9416b2eccf41a3f54f174410456e89e930001740a0de3465d80845  ha_energy_price_engine-manual.zip
```

## Delivered beta.2 scope

Six native stages: site/official source, grid, supplier, national charges/tax,
display, Review/Save & verify. Source-specific controls hide entity/unit fields for
official Nord Pool; verified configured area hints suggest DK2/Copenhagen where
supported; input is automatic DKK/MWh ex VAT, spot/grid VAT input 25 means 25%.
EWII and heating never infer private values. Advanced dated rates, locks/time bands,
manual overrides, backups and price breakdown remain accessible from Review.

Submitted drafts, invalid inputs and Back edits persist separately from active
settings; explicit Discard requires confirmation; Save returns to unapplied pages.
Unchanged Save triggers one reload/verification too. Existing incomplete sites
resume. Config v3 migration preserves IDs/names/source refs/rules and SQLite history;
tests execute actual released beta.1 code to seed bytes/rows/revisions before upgrade.
Canonical DKK sensors/statistics/storage and read-only CM API v1 remain unchanged.
Five unit-specific preferred-display entities default to øre/kWh; switching units
never reinterprets old statistics. Device sw_version derives from installed manifest.
Missing-component diagnostics report date/offset, source/failure and corrective action.
No fabricated zero, tariff arithmetic or persistence algorithm rewrite.

Actual real HA .4 frontend 20260930.5 + Playwright/system Chromium checks passed at
1440x1000 desktop and 390x844 mobile: all stages/Back, confirmed source defaults,
invalid-timezone retention/recovery, draft close/reopen, explicit Discard, new-site
Save, mobile Options Save and device version. Mobile has no horizontal overflow;
final mobile console/errors empty. Browser plugin absent; only decorative icon
requests substituted to avoid unavailable external requests blocking JS downloads.
Synthetic read-only sources; no owner login. This found/fixed ZoneInfo validation
import/disk work on HA's loop; regression asserts executor-thread validation.

## Exact owner update and limits

HACS → Energy Price Engine → Download/Redownload → Show beta versions → select
**v0.1.0-beta.2** → Download → restart HA. Existing site: Devices & services →
Energy Price Engine → **Configure**, not delete/recreate. Check device version,
review the six stages, **Continue** each draft page, then **Save & verify**; confirm
readiness before consuming prices. Guides: docs/HACS_DISTRIBUTION.md,
docs/WIZARD_GUIDE.md (actual synthetic QA screenshots), docs/BETA_SETUP.md and
explicit docs/BETA_ACCEPTANCE.md checklist.

No software publication blocker remains. Important native HA limit: Close/reload
never submits fields still being typed. Every page explicitly warns to Continue
first; submitted error/Back drafts survive interruption/restart. This is not
keystroke autosave. Avoid simultaneous browser editing flows for the same site.
Owner PAHA02-DEV/hardware/source/billing acceptance remains separate; isolated QA
is not a claim of owner access or physical mobile/Pi performance. All price history
remains in RAM and is not silently pruned. Unknown future/private rates remain
unavailable; EWII household .030 DKK/kWh ex VAT is June–September 2026 only.
No stable release, main merge, CM release, production HA, Node-RED or controls.

The remaining sections preserve completed beta.1 history and earlier measurements.
Their old next-step instructions are historical and do not reopen the completed mission.

## Completed PE beta.1 publication — final receipt

**Published and independently verified**, 2026-10-26. Public prerelease:
https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases/tag/v0.1.0-beta.1

- PR #7 merged normally at **56cdb3c10993179371483812cbc36f651ba3ad8e**.
- Main is HACS-compliant and remains at that release source. No history rewrite,
  force push, protection bypass or default-branch setting change occurred.
- Annotated tag **v0.1.0-beta.1** resolves to exactly that source; tag object
  **b971f31855c9fb9386eaa679a9c26cd94d4273a8**. Tag was never moved.
- Non-draft GitHub **prerelease** includes both ZIPs, BUILD_MANIFEST and SHA256SUMS.
  No stable release or CM publication. All ten actual source checks (main/tag)
  succeeded, including HACS, hassfest, both-core full tests and independent install.
- **177 tests per HA 2026.10.3/2026.10.4**, 91% coverage, zero skips. Full pinned
  consumer suites/coupled runtimes remain green, with both startup orders.
- Independently downloaded actual public metadata, source ZIP and all four assets.
  Tag/source, GitHub digests, ZIP SHA256SUMS, manifest provenance and every runtime
  file match. Unauthenticated public release HTTP200. Actual pinned HACS code passed
  add/beta discovery/exact tag capability/download/extraction/update/uninstall/
  reinstall using those public bytes on BOTH HA cores. Both downloaded ZIP layouts
  passed outside-source native setup/Options/SQLite reload/delete/recreate on both.
- Machine receipt: **docs/receipts/v0.1.0-beta.1.json**. Exact owner instructions:
  **docs/HACS_DISTRIBUTION.md**. No owner HA session was accessed; isolated testing
  does not assert authenticated PAHA02-DEV/frontend or Pi hardware acceptance.

The cloud upload restriction was resolved by the narrowly scoped publisher run
40392618234 on the preserved development branch. Main/tag source remain immutable.
Final receipt/handoff-only checkpoint subject: `docs: record published beta.1 verification`;
this development checkpoint is not a different release source and creates no release.
Publication mission is complete. Stop; do not start CM work or unrelated features.
Any production/cutover/stable/CM publication requires separate authorization.

## Publication execution checkpoint — 2026-10-26

PR #7 is merged normally (history preserved, no protection bypass) at
**56cdb3c10993179371483812cbc36f651ba3ad8e**. Actual merged main passes all five
remote checks, 177 local tests on both HA cores, Ruff, official hassfest and clean
both-layout independent native install. Main now contains the full integration.
Annotated tag **v0.1.0-beta.1** points to that exact source; tag object
b971f31855c9fb9386eaa679a9c26cd94d4273a8. No tag was moved/force-pushed.

Cloud `gh release create` could create its temporary release but asset upload to
uploads.github.com returned Forbidden; the CLI removed its incomplete draft. No
prerelease was published by that failed attempt. Public asset download/codeload
network preflights work. A narrowly scoped GitHub Actions publisher on this preserved
development branch now targets ONLY the existing authorized tag/source, waits for
all exact-source CI checks, rebuilds clean, smokes both archives and publishes the
prerelease with four provenance assets from the runner's supported upload route.
It cannot publish a stable/CM release or change/move a tag. Workflow change is part
of this authorized PE publication mission; main/tag source remain unchanged.

Checkpoint subject: `ci: publish authorized beta through GitHub runner`.
Next: verify the publisher completes, independently download actual public
metadata/source/assets with tools/verify_public_release.py, run HACS/native public
byte tests, then record the final receipt. Do not stop at a draft/failed upload.

## Authorized PE beta.1 publication mission

On 2026-10-26 the owner explicitly authorized: complete PE HACS integration,
merge existing PR #7 into main without force/protection bypass, and publish
**v0.1.0-beta.1 as a GitHub prerelease**. Do not stop at a candidate/draft. This
supersedes the prior PE distribution approval gate. It authorizes neither a stable
release nor EV Charge Manager publication nor live HA/Node-RED/device operations.
No new CM development is in scope; unchanged consumer tests remain compatibility
checks. No PAHA01/production access or PAHA02-DEV mutation is performed here.

Resumed validated baseline `bb71585654b431e61aa256657ab18d8c0f571cf0`, all ten
exact-head checks green. Existing runtime/SQLite/API architecture is preserved.
HACS metadata now uses the same display name as native HA: **Energy Price Engine**.
New prerelease tests run actual HACS registration, beta visibility, version selection,
`async_download_repository` capability checks, tag download/extraction, update,
uninstall/reinstall on published HACS 2.0.5 and pinned upstream code. The public
verification tool will download actual release metadata/source/assets, check source
identity and all payload hashes, and rerun HACS plus outside-source native install.
The historical empty-main snapshots remain a regression, not a claim about the
post-merge branch. Exact owner instructions are docs/HACS_DISTRIBUTION.md.

Preparation checkpoint subject: `release: prepare authorized HACS beta.1 publication`.
Local baseline release suites: **177 passed on HA 2026.10.3 and 2026.10.4**, zero
skips, 91% coverage; Ruff clean. New HACS download entry-point cases pass separately.
Commit/push, wait for exact-head CI, make PR #7 ready, then normal history-preserving
merge with expected head SHA. GitHub enforces its protections; do not use admin or
force bypass. Protection-settings GET returned HTTP403 for this integration token;
normal repository ruleset listing returned no rulesets. This is not permission to
bypass the merge API or required checks.

After merge, check out exact merged main, run required tests/CI/package smoke, build
clean archives, create the annotated beta tag at that validated commit, publish a
non-draft prerelease with both ZIPs/manifest/checksums, then independently verify
public tag/release/assets and isolated real HACS/native install. Record actual
merge/tag/source/check results in the final handoff/PR/release receipt. No success
claim until those actions complete. No release exists at preparation time.

## Checkpoints and validation

- Resumed `8ef40b74bff2b7a4359b18c37de598e6ce061e51`: ten checks green; original
  application `e6090a9`, 146 tests on both HA cores; package independently loaded.
- Native status/source/latest-consumer checkpoint **`3bdfb3b`**: 164 local tests on
  both cores, 92% coverage, zero skips; all **ten exact-head remote checks green**,
  including latest CM #25/#26 full suites and coupled runtimes.
- HACS workflow checkpoint **`561c9f781280b17533a337c4301492264d12b12a`** has
  all **ten exact-head remote checks green**, including actual HACS workflows and
  full latest consumers on both cores.
- Final application checkpoint **`ba855e2ba1a187a940311f4589174a34c67bad2d`** has
  all **ten exact-head checks green**.
- Final test/handoff checkpoint subject: **`test: cover consumer-first startup and HACS branch downloads`**.
  **175 tests pass on BOTH HA 2026.10.3 and 2026.10.4**, zero skips, 91% coverage,
  ResourceWarnings errors. Two upstream HACS deprecation warnings remain visible.
  Final local reruns pass after adding original source-unit/VAT/verification and
  manual source proof in the selected-slot view. Daily aggregate regression uses
  varied negative and positive prices, with distinct independent expected min/max/mean.
  Ruff check/format clean; both-layout native lifecycle smoke passed at 561c9f7.
  Both clean archive layouts passed native lifecycle smoke on BOTH cores.
  Final test/handoff checkpoint CI repeats after this push. Latest official HA release was
  rechecked on GitHub: 2026.10.4 (published 2026-10-24), matching the current lock.
- The ten new HACS tests execute unchanged published 2.0.5
  `c0dfd8b44297c3673c21973e2539375a53687a9c` and upstream
  `a15e87ec0d1c82e58f1ddbaf17669d3eaa261eb8`. Both current main trees reproduce the
  exact rejection. PE and CM #26 candidate trees pass actual registration, archive
  download/extraction, update backup, uninstall and reinstall in temporary HA paths.
  GitHub metadata/content/archive transport is mocked; validator/installer methods
  are not replaced. HACS backup directories are isolated per test; the actual backup
  implementation is retained. This is not a live authenticated frontend session.
- Latest CM PR #25 full suite **227 passed**, #26 **228 passed** on HA .4; actual
  coupled runtimes pass. CI at 561c9f7 also passed them on fixture-supported HA .3.
  Earlier unchanged CM #15/#16 suites remain **153/176** and still run in CI.

Additional final regressions: both producer-first and **consumer-first** startup
pass for ALL FOUR pinned CM lines on BOTH HA cores (eight actual runtime scenarios
per core). Consumer-first stays degraded with no valid forecast until PE loads,
then recovers within the existing 65-second simulated retry window; revisions,
duplicate suppression and producer unload remain safe with control/local-fetch/
consumer-composition paths prohibited. No consumer source changes.
HACS download transport now explicitly returns not-found for the nonexistent main
tag and requires the actual **heads/main branch-archive fallback**. All ten HACS
workflow cases pass on both cores with this realistic no-release transport fixture.
No HACS code/installer logic is replaced and no tag is manufactured.

Final application ZIP hashes (unchanged by the final test/handoff-only commit):
HACS-root `2d5d205d4151c28c15d280df4ee6fa161b9fb86cea4c8ca94b316530cddb801e`;
manual `3c14c07fb74c02a6389c10b0ab5ac54c9ea51a3970f5c2260a79961a584b074e`.
Rebuild clean for the final commit's BUILD_MANIFEST; dirty=false/published=false.
These are review/manual artifacts, not proof the blocked HACS default branch changed.

## Completed native software scope

PE alone owns retrieval, normalization, verification, tariff composition, permanent
15-minute final prices and publishing. No vehicle/charger controls. Reuses tested
CM PR #11 `5c32dc9` and PR #12 `9d949c6d0905646d1bbf973ea2edb47846e1607d`;
retain PROVENANCE.md and original golden fixtures (eight cases / 768 quarters).

- Native ConfigEntrySelector uses real opaque official Nord Pool IDs internally,
  rendered as readable HA entry titles. Safe unambiguous suggestions, explicit
  multiple-entry choice, Options/Reconfigure replacement without code edits.
  Legacy custom `nordpool` shadowing core is rejected. Actual core Nord Pool service
  schema/response tested with mocked market client; ex-VAT DKK/MWh converts once.
  Partial, duplicate, overlapping, shifted, hourly and nonfinite input cannot publish.
- One independently configurable entry/device per site, no arbitrary count cap.
  Explicit source/area/timezone, supplier label, dated rates/units/VAT, Radius C or
  manual tariff class/time bands, locks/fallbacks, taxes/eligibility, subscriptions,
  stable identity, Options draft/discard, migrations and repairs. No private rate
  copying. Missing components never zero. Settled rows cannot be silently repriced.
- Seven sensors/site: current and next-quarter price; complete-day min/max/average;
  current and tomorrow readiness. Minute publication handles midnight/freshness.
  Readiness attributes expose chosen source, site, currency, resolution, coverage,
  last verification/error and next scheduled check. Options stored-slot inspector
  shows UTC/local-offset identity, component/VAT amounts, effective/verification
  periods, original revisions and excluded monthly subscriptions. Reads do not
  fetch or perform tariff composition. Diagnostics redact private labels/references.
- Refresh requirements preserved in Copenhagen: 13:05, conditional 13:20/13:40/
  23:59, unconditional 00:01, startup/reload/source recovery. Real verification times
  are not promoted merely by reading cached data. Late provider startup, new registry
  entities and reload recover without waiting for the next afternoon publication.
- Read-only Python API v1 remains authoritative; immutable synchronous indexed
  snapshots, explicit READY/INCOMPLETE/STALE/ERROR/NOT_LOADED, additive producer-entry
  identity, machine schema/fixtures and exact prior-revision lookup. No old service
  transport or duplicated consumer tariff arithmetic was introduced.
- Transactional executor SQLite with row/provenance checksums, stale-writer guard,
  atomic corrections/revisions, real interrupted writer and I/O-failure recovery,
  corruption fails closed, verified backup/offline restore and non-destructive JSON
  migration. New tests read concurrently during a blocked disk commit and recover
  three independent year-long site histories, with unchanged historical amounts.
- Deterministic licensed HACS-root/manual ZIPs, commit/file hashes and dirty-tree
  guard. Outside-source-tree native setup/options/reload/delete/recreate smoke now
  preserves the old ledger and prevents silent inheritance by a replacement entry.
  Actual HACS package tests are additional to these ZIP tests, not conflated with them.

EWII household markup **0.030 DKK/kWh ex VAT applies June–September 2026 only**.
No current October/future/other-site contract invented. National baselines are bounded
and opt-in: 2026 TSO net .043/system .072; 2026–2027 electricity tax .008 ex VAT.
Future/reduced-tax terms require explicit verified rules/eligibility, never guesses.

## Consumer references and reproducibility

Immutable test exports (not deployed PE dependencies), unchanged consumer sources:

- #15 `0a28438d1cfa5cc8136417f1520a891faa67b979`.
- #16 measured history `23bf84b2488372d9708164a4b42df3fd109b7726`.
- #25 packaged beta `1246ccff25ee36f705e7c503499317f58802d7a2`.
- #26 acknowledgment hardening `5ef7115a9599e1ff25019e91b3737500853b9a38` (latest).

Python 3.14.8; fixture 0.13.374 pins HA .3. Current-HA hash lock explicitly overrides
that test-only pin to .4; no TLS/hash/check bypass and no fixture runtime dependency.
Node 24+ runs original JavaScript parity tests. No live service/secrets required.

```sh
uv venv --python 3.14.8
uv pip sync --require-hashes requirements-dev.lock
.venv/bin/python tools/prepare_consumer_refs.py
.venv/bin/python tools/prepare_hacs_reference.py
.venv/bin/ruff check custom_components tests tools
.venv/bin/ruff format --check custom_components tests tools
.venv/bin/pytest --cov=custom_components.ha_energy_price_engine -W error::ResourceWarning
.venv/bin/python tools/test_two_runtime.py --consumer pr26
.venv/bin/python tools/run_consumer_suite.py --consumer pr26
.venv/bin/python tools/build_beta.py
.venv/bin/python tools/smoke_install_package.py dist/ha_energy_price_engine.zip
.venv/bin/python tools/smoke_install_package.py dist/ha_energy_price_engine-manual.zip
gh pr checks 7 --repo NicolaiTandrup/HA-Energy-Price-Engine
```

Repeat in an independent venv with requirements-ha-current.lock. CI executes all
four consumer lines on both cores plus actual HACS workflows, official hassfest,
HACS metadata validation and clean independent package install. Download final exact
head Actions artifacts or build clean; use BUILD_MANIFEST/SHA256SUMS. Old archive
hashes from e6090a9 are superseded. Artifact redirect host previously returned 403
in this cloud; do not claim a downloaded-CI-byte comparison if that persists.

## Remaining gates and limits

PE merge and beta.1 prerelease publication are now explicitly authorized above.
The current mission must resolve its distribution implementation and independently
verify public downloads. Actual PAHA02-DEV observations remain owner-run hardware
acceptance and must not be fabricated; isolated verification is permitted. For real read-only pilot acceptance, obtain actual current
per-site supplier terms and recorded legacy/billing/plan exports, then compare offline
with explicit units/VAT/site mapping. No simultaneous live legacy/official brokers.

Cloud benchmarks preserve the SQLite improvement: year append 96 rows ~.030s versus
JSON ~1.675s; five-year append .115s, reload 4.519s, 69.6MB database. See PERFORMANCE.md
and raw reports. These are NOT Raspberry Pi evidence. Five-year whole-process peak
~647MiB includes multiple engines/synthetic inputs; all history stays in RAM for API
v1. No reference-acknowledgment/archival API exists to safely prune accounting data.
Storage/RAM is therefore not arbitrarily bounded. Diagnostics expose real bytes/free
space and this policy. Measure Pi resource limits before acceptance; if insufficient,
implement compatible async historical paging/reference-aware archival, never silent
history deletion. Multi-site cloud tests do not close that hardware gate.

CM #26 now has a durable executor with independent acknowledgment hardening, but
actual provider transport/session/physical acknowledgment commissioning remains
separate from PE/API tests. Keep commands disabled until independently accepted and
explicitly authorized. Rollback must restore BOTH the legacy Nordpool dependency
and the exact Brain, Energy Price Broker and Charger Optimizer flow/config backups.

Next: complete the authorized merge/prerelease/public verification sequence above.
Preserve exact tag/commit/asset provenance and existing branch history. No stable
release, CM publication, production HA/Node-RED changes or live controls.

## Beta.5 diagnostic and release-validation checkpoint

Checkpoint subject: **fix: show missing components before future activation guidance**.
Known prior commit d8e54e2; all10 push/PR checks green there. Future activation now
reports missing supplier/components first, including next-day activation at midnight.
Only a verified activation range shows the wait-for-quarter guidance. Native details
say until changed instead of the internal9999 sentinel; national details are scoped
to national/VAT rows, and unavailable public-offer discovery is explicit.

Final local producer suites **234 passed per core** (2026.10.3/.4), **88%** coverage,
zero skips, two pinned upstream HACS deprecation warnings. Focused diagnostic12
passed; ruff check/format passed. Real native DA public EWII Plus and EN custom
journeys save accepted pages, close/resume tax and show verified expected prices.
EN mobile missing supplier and approved provisional case passed, width390 with no
horizontal overflow or frontend errors. No draft-final-save needed. Restart/deletion
and final captures are in progress. Public setup/HACS/acceptance docs updated to
five saved stages; software/owner acceptance boxes intentionally pending final gates.
No beta.5 tag/release yet. Next: finish evidence, unchanged consumer matrix, package
and metadata gates, commit clean source, exact-source CI, immutable authorized
prerelease, independent public validation, final handoff and stop.

## Beta.5 native acceptance evidence and clean-source checkpoint

Checkpoint subject: **docs: record beta.5 native journeys and release candidate evidence**.
Runtime source6d1ef58. Final local producer234/core,88% coverage,zero skips;
all four unchanged consumer suites153/176/227/228/core and2 actual coupled runtime
cases per consumer/core passed. PyPI current stable independently rechecked .4.
Both clean archive layouts installed/imported outside source on both cores,1 native
smoke/layout/core. Official local hassfest1integration,0invalid. Full source CI at
6d1ef58 correctly rejected a test-host name introduced in the public guide after
local suite execution; corrected to generic wording, privacy/package doc gate rerun.
No test disabled or weakened. Exact final-source push/PR/tag CI remains required.

Actual disposable HA .4/frontend20260930.5 EN/DA desktop1440x1000/mobile390x844:
custom contract11.1ore exVAT gives.6675DKK; official quoted Plus6.5ore with an
explicit fictional incl-VAT customer confirmation gives.59375DKK; approved12.4ore
incl-VAT estimate gives.65275DKK and zero ledger rows/no authoritative READY.
Ordinary custom rates need no dates. Each accepted step is actual saved config;
close/reopen resumes tax; direct edits return review, with no final save. Grid
outage removes final readiness and direct corrective settings work; recovery and
explicit check restore verified prices. Both languages fit mobile width390,zero
frontend errors. Two short native webm demos and19 screenshots committed.

Real clone upgrade preserves four beta.4 sites' settings/IDs/source mappings and
historical decoded SQL rows. Restart preserves nine site configurations and all
settled rows/revisions; no past unknown quarter backfilled. Wrong permanent-delete
confirmation rejected; accepted cleanup removed only selected115-row site, including
setup progress. Same-name recreate has a new ID, no contract and empty history.
Other sites and global recorder inode retained. Detailed synthetic receipt:
`docs/receipts/v0.1.0-beta.5-simulation.json`. Owner acceptance is explicitly false.

SQLite repeat during concurrent cloud validation:35136rows/18239488bytes,
96-row append.0457s,reload2.240s,lookup10.06us,peak243448KiB. Original transactional
touched-row persistence retained; cloud results do not establish Pi performance.
Public guides now cover five saved stages, fresh public offers/VAT confirmation,
standing current agreements and preserved future overrides, partial first-day
coverage, diagnostics, HACS upgrade and safe selected-site reset.

Next: commit clean source and await every exact-source check, build/hash clean
source, tag beta.5 immutably, run fixed-source publisher with15 green checks and
both-layout native installation gates. Independently verify public release/assets/
HACS/version selection on both cores, update receipt/PR/handoff and stop. No stable,
main merge or owner equipment access. No beta.5 publication claimed yet.

## Beta.5 immutable release orchestration

Checkpoint subject: **ci: publish immutable beta.5 with independent public verification**.
Release source **a4ede923e42573def49026a8d1d817c37a979171**, clean build. All10
push/PR checks green, independently visible on public GitHub source checks. Annotated
v0.1.0-beta.5 object **7a919061010e1a018a54235e96711ff4295622a7** pushed; source/tag
never moved.13 exact-source jobs green at this checkpoint; tag core jobs pending.
Publisher refuses publication unless all15 exact-source jobs are successful, source/
annotated object match, clean deterministic hashes match, and both independent native
archive installations pass. Existing matching release is verified without replacing
any assets; mismatches stop publication. Main and prior beta tags remain preserved.

SHA256 root9f8ea839a04b5d67f61dc0e49f11611abcb4c85cdfced809f813937548dc0ad0;
manual422c5d1bb39c4596a4af36db2e325ad56b642b8287e2bc09409d96a5928d3036.
Native QA server stopped after evidence collection; no owner HA/control access.

After cloud environment reconnect, api.github.com requests began failing at the
proxy CONNECT layer(403); github.com web/Git/codeload still work. Existing saved
environment draft includes the API hostname, but saved policy is not proof of live
access. No credentials extracted/replaced, no verification bypass. API-based
publication and independent postpublication verification run on authorized GitHub
runners. Two fresh locked core jobs independently download public metadata/assets/
source/main, verify digests and actual unchanged HACS workflows plus both native ZIP
layouts, and test actual public semantic release selection. Audit commits permanent
receipt and updates existing PR14 only after both pass. Local read-only public
release/assets/tag checks and final handoff still follow. No beta.5 publication
claimed at this checkpoint. Stop after authorized beta publication and verification.
