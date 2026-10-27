# Development handoff

Updated 2026-10-27 (Europe/Copenhagen). Read AGENTS.md first. This is the single
permanent handoff. Beta.2 mission is complete: **published and independently verified**.
Stop here unless the owner requests further development. Existing history and PRs
are preserved; no worktree, force push, main merge or production change occurred.

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
