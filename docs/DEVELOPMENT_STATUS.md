# Development handoff

Updated 2026-10-25. Read AGENTS.md first. This is the single permanent handoff.

## Extended run checkpoint — 2026-10-25

Resumed validated final head `8ef40b74bff2b7a4359b18c37de598e6ce061e51` (all ten CI
checks confirmed green). Read all five open issues and current PR receipts. Native
Nord Pool already used HA ConfigEntrySelector; added a real opaque-ID selection /
replacement regression with readable source titles, no text-entry workaround.
Added seven total entities/site (current, next, complete-day min/max/average,
readiness and tomorrow); source health/refresh/completeness/next scheduled check
are attributes. Options now offers a bounded today/tomorrow stored-slot inspector
with UTC offsets, original components/VAT/revision/verification and excluded fixed
subscriptions. Reads neither fetch nor compose. Official input now rejects hourly
resolution and off-quarter boundaries; actual core service tests reject partial,
duplicate, overlapping, shifted, hourly and nonfinite source rows.

Local **164 tests pass on both HA 2026.10.3 and 2026.10.4**, 92% coverage, zero skips,
ResourceWarnings errors. Real three-site year-long SQLite histories and concurrent
reads during an actual blocked disk commit pass, preserving old snapshots until
commit and exact settled rows on recovery. Official local hassfest passes.
Latest pinned CM #25 `1246ccff25ee36f705e7c503499317f58802d7a2` full **227** tests and
#26 `5ef7115a9599e1ff25019e91b3737500853b9a38` **228** tests pass on HA .4; coupled
runtime tests pass. CI now also exercises these unchanged suites plus original
#15/#16 and shared machine fixtures. Supported-HA latest CM runs follow in CI.
Checkpoint subject: `feat: expose native price status and verify latest consumers`.

**Critical HACS distribution finding:** owner reports both PE and CM custom repo
adds rejected because main contains only LICENSE/README. Passing HACS action or ZIP
smoke is NOT an actual HACS installation. Current native code remains on draft
branches. Never claim ordinary HACS installability until the default-branch gate
is resolved with explicit owner approval. No merge/default-branch change/release
is authorized. Next priority: pinned actual HACS add/download workflow tests,
non-destructive owner-reviewable distribution strategy and exact PAHA02-DEV guide.
Manual ZIP remains independently testable but does not satisfy the requested HACS
distribution gate. Storage remains history-preserving/unpruned; Pi resource bounds
require real measurement and a future reference-aware archival design.

## Resume point

Existing branch `feat/standalone-price-engine`, existing draft PR #7; proposed
`v0.1.0-beta.1`. Continue this checkout, do not restart implementation. Previous
validated application checkpoint `c88c6ae852b496930464fca96d11aa45efdccf4f` had all
eight exact-head CI checks green. Validated beta application commit **`e6090a9f66a2acfcda59c6c553142eb0de3c8c5e`**.
Final handoff/CI identity checkpoint subject:
`docs: record validated beta candidate and publication gates`.
This document cannot contain its own final commit hash.

No live HA, Node-RED, vehicle/charger commands, merge, tag or release publication
has occurred. Owner separately authorizes publication and any actual cutover.

## Completed Issues #1–#5 software scope

- Independent native integration; arbitrary repeatable per-site config entries,
  devices/sensors, Options, Reconfigure, entry migration, repairs and diagnostics.
  Explicit stable site/entry identity; no private rates copied between sites.
- Official built-in Nord Pool discovery and read-only service use, rejecting a
  shadowing legacy HACS component. Real HA service schema/response tested with a
  mocked market client. Generic timestamped entity sources require explicit units,
  VAT and genuine provider verification. Late provider startup/reload/new entities
  trigger recovery; failed verification publishes degraded readiness.
- Native dated supplier/DSO/TSO/tax/VAT/subscription editing, local-hour tariff
  bands, manual locks, safe automatic Radius C and explicit fallback. Overlaps and
  missing coverage fail closed. Fixed monthly charges never affect marginal price.
  EWII 0.030 DKK/kWh ex VAT is a household June–September 2026 fact only. No
  October/future/summer-house contract guessed. National baselines are bounded.
- Persistent final 15-minute prices; 92/96/100-slot DST; immutable settled quarters,
  targeted future repricing, durable correction audit and exact prior revisions.
  Refreshes preserved: 13:05, conditional 13:20/13:40/23:59, unconditional 00:01,
  startup/reconnection. Stale full coverage cannot suppress rescue. Midnight sensors
  read the new quarter instead of advertising yesterday's readiness.
- Read-only Python API v1 is authoritative. Immutable synchronous memory lookups,
  no retrieval/arithmetic/disk mutation, explicit degraded statuses. Additive
  producer-entry identity and machine serialization/schema preserve existing users.
  No obsolete service transport added; PR #6 acknowledges supersession.
- Transactional SQLite, checksummed rows/deduplicated provenance, optimistic
  stale-writer guard, executor disk work, failed/interrupted commit recovery,
  valid preview JSON migration without deletion, corrupt history fails closed.
  Verified snapshot/inspect/export/offline restore preserve original bytes.
- Deterministic licensed HACS-root and manual ZIPs, exact commit/file hashes,
  clean-tree build guard, isolated installation/import/config/options/SQLite reload
  smoke tests, HACS/hassfest metadata, English translations and CI packaging.
- Recorded legacy comparison tooling validates explicit sites/UTC/unit/VAT,
  differences and gaps. No simultaneous live legacy/official broker requirement.
  Complete setup and acceptance/atomic source migration/rollback guides are
  `docs/BETA_SETUP.md` and `docs/BETA_ACCEPTANCE.md`.

## Provenance and consumers

Reused tested EV Charge Manager PR #11 `5c32dc9` and PR #12
`9d949c6d0905646d1bbf973ea2edb47846e1607d`; see PROVENANCE.md. Eight independently
regenerated original seasonal/DST/VAT golden scenarios cover 768 quarters.
Consumer exports are immutable test dependencies, not deployed PE dependencies:
PR #15 `0a28438d1cfa5cc8136417f1520a891faa67b979`, PR #16 reconciled measured-history
`23bf84b2488372d9708164a4b42df3fd109b7726`. Do not replace #15 with the older service
proposal or lose #16's measured history. Actual separate runtimes test revisions,
duplicate replan suppression and producer-unload invalidation with local consumer
retrieval/calculation/control prohibited. Native API fixtures cover both callers.

## Validation at this checkpoint

- Python 3.14.8; **146 tests, zero skips, 91% coverage** on BOTH HA 2026.10.3 and
  current HA 2026.10.4. ResourceWarnings are errors. Ruff check/format clean.
- Official local hassfest: one integration, zero invalid.
- Unchanged full pinned consumer suites against current HA: PR #15 **153 passed**,
  PR #16 **176 passed**, each 91% coverage. Runner isolates the existing fixture's
  shared disk directory; no consumer sources or stale-writer safeguards weakened.
  Node 24+ is required for the existing JavaScript parity tests.
- Supported-HA full consumer suites also pass **153 / 176**; both coupled-runtime
  checks pass on BOTH cores. Both clean committed archive layouts pass independent
  install/import/config/options/SQLite reload on BOTH cores.
- All **ten exact-head remote CI checks passed at e6090a9**: two HA targets,
  HACS, hassfest and independent beta install, each on push and PR. Push package
  run `40178336545` has the head-commit artifact; PR run `40178339787` originally
  recorded GitHub's synthetic merge SHA. Final workflow explicitly checks out PR
  head for package identity. Final handoff-only/CI-identity checkpoint rerun follows.
- Clean archive SHA-256: HACS-root
  `48dd5a2add286538c57a87c2ccf8891b880742e0cf8658ea82db53ce253dedb7`; manual
  `9aea596d4213e5f4746036d45ffc9f11a38f1b4704ee2eff44a393fc7b0f6ee0`.
  BUILD_MANIFEST says dirty=false, published=false. No runtime changes follow
  e6090a9, so these runtime archive hashes remain applicable.
- Cloud artifact-download redirect host returned HTTP403; GitHub confirms the
  uploaded artifact and passing independent installation job. Local clean ZIPs
  remain available in dist; do not claim a downloaded-CI-byte comparison occurred.
- Latest fixture 0.13.374 pins HA 2026.10.3. The second hash-locked environment
  explicitly overrides that test-only HA pin to 2026.10.4. Hash/TLS verification and
  all required checks remain enabled; runtime has no added dependency on fixtures.

## Performance and limitations

Actual cloud x86_64 reports in docs/benchmarks and PERFORMANCE.md:
35,136 rows +96 append: JSON 1.675 s /69.5 MB versus SQLite 0.0297 s /18.2 MB.
Five-year 175,296 rows: append 0.115 s, reload 4.519 s, ~5.8 microsecond 96-row
lookup, 69.6 MB SQLite. CI additionally prohibits rewriting historic rows with an
actual SQLite trigger while appending a day to a year of history.
Five-year benchmark whole-process peak ~647 MiB includes HA imports, synthetic
inputs and original/restored engines. History remains memory resident for API v1;
no automatic retention pruning or arbitrary resource guarantee. These measurements
DO NOT establish Raspberry Pi throughput/RAM or live provider availability.

## Publication blockers versus pilot gates

No known application build blocker: exact-head CI and clean archive installation
verification passed for the application commit above. **Owner publication
authorization remains absent**;
no tag/prerelease/merge is authorized. Ordinary HACS default-branch/release download
is not yet available while code is an unmerged draft; reviewed ZIP installation is
independent of that distribution gate.

Production pilot additionally needs recorded household/summer-house legacy/billing
exports and known-good plans, actual current per-site supplier terms, approved
HA OS/Raspberry Pi resource/source testing, and independent real CM command-executor
acceptance if control is desired. Automated mocked-source tests cannot supply that
evidence. Restore BOTH the legacy Nordpool dependency and exact saved Brain,
Energy Price Broker and Charger Optimizer flows on rollback. Actual source migration
and granting live commands require distinct explicit owner approval at cutover.

## Reproduce and next actions

```sh
uv venv && uv pip sync --require-hashes requirements-dev.lock
.venv/bin/python tools/prepare_consumer_refs.py
.venv/bin/ruff check custom_components tests tools
.venv/bin/ruff format --check custom_components tests tools
.venv/bin/pytest --cov=custom_components.ha_energy_price_engine -W error::ResourceWarning
.venv/bin/python tools/test_two_runtime.py --consumer pr15
.venv/bin/python tools/test_two_runtime.py --consumer pr16
.venv/bin/python tools/run_consumer_suite.py --consumer pr15
.venv/bin/python tools/run_consumer_suite.py --consumer pr16
.venv/bin/python tools/build_beta.py
.venv/bin/python tools/smoke_install_package.py dist/ha_energy_price_engine.zip
.venv/bin/python tools/smoke_install_package.py dist/ha_energy_price_engine-manual.zip
gh pr checks 7 --repo NicolaiTandrup/HA-Energy-Price-Engine
```

Repeat in an independent venv with requirements-ha-current.lock. CI does both,
plus official hassfest/HACS and clean package artifact installation. Next: verify final handoff-only/CI-identity checkpoint checks, then owner review
of the candidate/checksums and acceptance checklist. If CI fails, resolve without
bypasses. Never auto-close pilot acceptance issues from synthetic tests.

Reusable cloud setup draft already saves Python/hash-lock/existing-checkout workflow;
no service or secrets required. Git/GitHub API work; use REST PR updates if gh's
legacy projectCards GraphQL query fails. Saving environment configuration is separate
from publishing a cloud snapshot and separate again from integration release.
