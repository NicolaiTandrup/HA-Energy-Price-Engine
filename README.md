# Home Assistant Energy Price Engine

**Proposed v0.1.0-beta.1 — HACS distribution blocked.** Native Home Assistant
software candidate on [draft PR #7](https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/pull/7).
Both repositories’ main branches lack integration code; normal HACS custom-repository
installation is currently rejected. This beta is not complete as an owner-installable
HACS beta. See the [distribution gate and exact PAHA02-DEV procedure](docs/HACS_DISTRIBUTION.md).
No release has been published and no production cutover is authorized by this code.

The standalone `ha_energy_price_engine` owns electricity price retrieval, tariff
verification, calculation, permanent 15-minute final prices and publishing. EV
Charge Manager, heating and batteries consume the read-only API. There are no
vehicle or charging controls here. The tested EV PR #11/#12 pricing implementation
is reused with [provenance retained](docs/PROVENANCE.md).

**[Installation and native setup](docs/BETA_SETUP.md)** ·
**[Beta acceptance / migration / rollback](docs/BETA_ACCEPTANCE.md)** ·
[API v1](docs/API.md) · [Storage/recovery](docs/ADR-002-ledger-storage.md) ·
[Measured performance](docs/PERFORMANCE.md) · [Permanent handoff](docs/DEVELOPMENT_STATUS.md)

Add one independent site per entry in **Settings → Devices & services → Energy
Price Engine**. Configure sources, supplier contracts, grid tariff class, dated
rates, units, VAT, time-of-use hours, locks/fallbacks and fixed subscriptions in native
Options. Sites have stable IDs and no hardcoded count limit; no private contract is
copied to another site. Safe discovery suggests only an unambiguous official Nord
Pool entry for confirmation, and rejects a legacy custom component shadowing it.

Final inclusive DKK/kWh prices use immutable UTC quarters, 92/96/100-slot local DST
days, negative prices, transactional SQLite persistence, revision/correction history
and read-only indexed lookups. Valid preview JSON ledgers migrate once; corrupted
history blocks writes instead of being discarded. Native backup, diagnostics and
repair flows expose actual applied sources/values and readiness. Missing prices
never become zero; subscriptions never affect marginal slot ranking.

Copenhagen refreshes remain **13:05**, conditional **13:20 / 13:40 / 23:59**, and
unconditional **00:01**, plus startup and bounded source-event recovery. Reads do
not fetch providers or recalculate tariffs. Consumers must check complete READY
coverage and explicit site identity. Actual PE+CM #15/#16 runtime conformance is
exercised with synthetic observations and no control calls.

The documented EWII **household** markup is **0.030 DKK/kWh excluding VAT for
June–September 2026 only**. It is not an October/current default or a summer-house
rate. Enter actual verified per-site terms. National baselines are explicitly bounded;
future supplier/TSO/tax rules are not invented. Recorded legacy comparisons replace
any requirement to co-run the legacy HACS broker and official Nord Pool integration.

## Candidate package and validation

CI builds reproducible HACS-root and manual-install ZIPs, file/commit metadata and
SHA-256 checksums, then installs them **outside the repository source tree** in a
fresh HA harness. Download the exact reviewed commit's **Beta candidate package**
artifact. HACS metadata/brand validation is included; ordinary HACS release discovery
requires separately authorized publication, not an unmerged default-branch promise.

Tests cover native multi-site flows/upgrades, real official HA Nord Pool service
plumbing with a mocked market client, units/VAT, overrides/time bands, source failures,
SQLite interruption/corruption/recovery, exact historical revisions, JSON contract
fixtures, actual PE+CM runtime interaction and archive installation. CI targets the
fixture-supported HA 2026.10.3 and current 2026.10.4 with documented test scaffolding.
Cloud scale benchmarks do **not** establish Raspberry Pi performance. Consult the
handoff for exact current counts/CI and the acceptance guide for remaining live gates.

## Development

Read AGENTS.md and the existing handoff first. Use this isolated checkout, Python
3.14.8, hash-verified locks and pinned read-only consumer exports:

```sh
uv venv --python 3.14.8
uv pip sync --require-hashes requirements-dev.lock
.venv/bin/python tools/prepare_consumer_refs.py
.venv/bin/python tools/prepare_hacs_reference.py
.venv/bin/pytest --cov=custom_components.ha_energy_price_engine -W error::ResourceWarning
.venv/bin/ruff check custom_components tests tools
.venv/bin/ruff format --check custom_components tests tools
.venv/bin/python tools/test_two_runtime.py --consumer pr15
.venv/bin/python tools/test_two_runtime.py --consumer pr16
docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest
.venv/bin/python tools/build_beta.py
```

No running HA service, secret, live Node-RED change or hardware access is needed for
the development tests. No merge, release publication or live deployment is performed.
