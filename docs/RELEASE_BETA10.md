# v0.1.0-beta.10 — minimal electricity price engine

**Breaking development prerelease for HACS. Back up and recreate older beta sites.**
API v2 replaces v1; unchanged unreleased EV Charge Manager needs the documented
adapter update. No stable release, main merge, production cutover or charging
control is part of this release.

PE now creates **nine sensors per site**, down from40+1 entities. One verified dated
pricing path, saved source/grid/supplier setup and one bundled card replace the
invoice/subscription/provisional/technical duplicate paths. Runtime Python shrinks
from37modules/7,214lines to22/3,226; translations shrink about92%. The validated
compressed SQLite ledger, revision history, Radius adapter, negative prices, DST and
required13:05/13:20/13:40/23:59/00:01 Copenhagen refresh schedule remain.

Daily statistics appear immediately from all verified schedule quarters, including
past and future. Otherwise the UI clearly labels a complete remaining-day range
with coverage. No unknown private history, rates or zero prices are invented.
Normal supplier/grid input starts next complete quarter; an explicit confirmation
can verify earlier today. Public charges expire at documented boundaries. EWII
household0.030DKK/kWh exVAT is only June–September2026, never a future/site default.

## Install on PAHA02-DEV

1. Back up development HA and record every site's actual rates/overrides. Enable
   **Show beta versions** in HACS, refresh, explicitly select **v0.1.0-beta.10**,
   download and restart HA. Reload the app/browser.
2. Older PE sites intentionally fail migration without deleting data. **Configure**
   opens the selected-site reset. After backup, type the exact site name and confirm
   deletion of only that site's PE history/config. Re-add each intended site with a
   new ID. Normal HA Delete retains history; no bulk `.storage` cleanup is needed.
3. Add/select official HA Nord Pool DK1/DK2; no legacy broker must run alongside it.
   Add PE: site/source → confirmed Radius C or manual grid → actual supplier markup
   in øre/kWh, with explicit VAT basis. Accepted steps save immediately; Done closes.
4. Device info must show0.1.0-beta.10 and nine sensors. Confirm availability and
   full/remaining-day coverage. Add more sites independently.
5. Register the bundled resource as a JavaScript module:
   `/ha_energy_price_engine/energy-price-engine-card.js?v=0.1.0-beta.10`.
   Paste this Manual card YAML; a single site is automatic and several offer a selector:

```yaml
type: custom:energy-price-engine-card
```

[Complete install/reset](HACS_DISTRIBUTION.md) · [Full dashboard YAML](dashboard.yaml)
· [Acceptance checklist](BETA_ACCEPTANCE.md) · [API v2](API.md) ·
[CM source-change handoff](INTEROPERABILITY.md) · [Before/after inventory](MVP_CLEANUP.md).

## Verification

112 tests per HA2026.10.3/2026.10.4 core,90%coverage,zero skips;18 locked desktop/mobile
browser cases;official hassfest/HACS CI;actual HACS2.0.5/upstream beta9→10 file update,
reinstall/uninstall;both native ZIP layouts installed/configured/reloaded outside
source.21 actual native HA.4 screenshots cover EN/DA, saved steps, bad input,
nine entities, full/remaining statistics, graphs/DSO/quarter/component tables,
multiple sites and selected-site reset. Two ledgers survived restart byte-identically;
reset preserved the other site's bytes. No provider requests on reads. Producer
unload clears old Ready graphs. [Recorded/synthetic receipt](receipts/v0.1.0-beta.10-simulation.json).

Both deterministic archives and their member hashes are in BUILD_MANIFEST.json;
SHA256SUMS records archive hashes. The guarded publisher verifies exact-source CI,
annotated tag, main and all prior beta1–9 assets before publishing. Fresh independent
post-publication jobs download public source/assets and test HACS/both layouts on
both cores; the publication receipt records their actual results.

## Remaining limits

CM API1 is incompatible and CM source is unchanged; use the precise handoff before
coupling. Older beta sites require explicit recreation after backup. Actual private
contracts, current provider availability, physical mobile/hardware and owner
PAHA02-DEV acceptance remain owner checks. All history is retained/indexed in memory;
cloud1/5year append benchmarks are0.043/0.136s but **do not establish Raspberry Pi
performance**. The card needs one resource registration and covers today/tomorrow.
No production HA, Node-RED, Tesla/Easee or physical controls were accessed.
