# Beta.10 acceptance checklist

Breaking development beta for PAHA02-DEV. Software evidence uses isolated HA and
recorded/synthetic prices, not owner hardware or live contract acceptance.

- [ ] Back up code/config/Recorder/.storage; record each actual contract/grid and dated override.
- [ ] HACS Show beta versions persists; explicitly download v0.1.0-beta.10 and restart.
- [ ] Device info shows0.1.0-beta.10; old beta sites fail safely until explicitly reset/recreated.
- [ ] Reset only the intended named site after backup; another site's data and Recorder survive.
- [ ] Official Nord Pool DK1/DK2 is selected; legacy domain shadowing is absent. No parallel broker required.
- [ ] Site/source, grid and supplier steps save; close/reopen resumes. Unsubmitted fields are clearly unsaved.
- [ ] Confirm actual Radius C or actual manual DSO. Enter real supplier markup in øre/kWh and correct VAT basis.
- [ ] Nine enabled sensors per new site; full precision internally, ordinary øre/kWh2decimals.
- [ ] Current/next raw and final match verified source/component arithmetic, including negative spot.
- [ ] Full-day stats include all92/96/100 quarters immediately when genuinely covered.
- [ ] New from-now private rate yields labeled remaining-day coverage, with no invented past prices.
- [ ] Middle gaps/expired components/source errors never create READY ranges or zero-filled prices.
- [ ] Bundled resource registered; minimal YAML discovers one site, named selector handles several.
- [ ] Two graphs, DSO intervals, all quarter rows and selected component/VAT/source details work desktop/mobile EN/DA.
- [ ] Native Options Done closes; restart/reload preserves the new site ID, stored quotes and revision references.
- [ ] Unreleased CM upgraded to API2 and tested separately before coupling. Unchanged API1 CM is unsupported.
- [ ] Public national effective dates and private contracts remain valid; no future EWII/heating inference.
- [ ] Development hardware storage/RAM/latency acceptable; cloud measurements are not Pi evidence.

Automated release gates: complete unit/native-flow/source/Radius/math/DST/statistics/
SQLite fault/revision/reset/read-only API/cost tests on HA2026.10.3 and2026.10.4;
locked desktop/mobile Chromium tests; actual pinned HACS install/update/reinstall;
official hassfest/HACS CI; both independently installed ZIP layouts; reproducible
clean archive hashes; native HA screenshots and restart; immutable prior releases/
main; exact-source CI before beta10-only guarded publication; fresh public source/
asset/download verification on both cores. Current results and remaining work are
recorded in [the permanent handoff](DEVELOPMENT_STATUS.md), not inferred from this list.

Owner boxes above are intentionally unchecked. No production HA, Node-RED or physical
charging controls may be changed by this acceptance run. No stable release/main merge.
