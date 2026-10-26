# Development instructions

Read this file and `docs/DEVELOPMENT_STATUS.md` first in every session. Inspect
Git status, history and the active PR before editing. Resume existing work from
evidence; preserve user changes. Use this isolated checkout; do not create a Git
worktree unless the owner explicitly requests one.

## Ownership and safety

`ha_energy_price_engine` alone owns retrieval, verification, calculation, tariff
sources, price history and publishing. Consumers only read versioned final prices.
Reuse the tested EV Charge Manager PR #11/#12 implementation and retain attribution.
Do not duplicate tariff arithmetic in consumers. Unknown prices are never zero.
Never modify live Home Assistant, Node-RED, vehicle or charging controls. Tests use
mocked read services. No stable release, merge or production cutover without owner
approval. Do not infer future contracts, rates or authorization from test success.
EWII household markup is documented as 0.030 DKK/kWh excluding VAT only for June
through September 2026; it is not a default for another site or later period.

## Checkpoints

Work in small cohesive, tested incremental commits. After each meaningful milestone,
update the same `docs/DEVELOPMENT_STATUS.md` with branch, known commit, completed
and pending issue work, exact local tests and actual remote CI, decisions, blockers
and precise next steps. A document cannot include its own final commit hash; use
the checkpoint subject for that commit. Commit and push throughout development;
post meaningful progress updates to the active draft PR/issue when access permits.
Before stopping, leave a coherent committed checkpoint and an accurate handoff.
Never claim pending/unrun checks passed. Do not add competing handoff documents.
