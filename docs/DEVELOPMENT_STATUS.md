# Development handoff

Updated 2026-10-24. This checkout remains docs-only branch
`docs/ev-consumer-contract-v1`, draft #6. **Its service proposal is superseded.**
Do not bootstrap or recreate producer implementation from this branch.

Actual independent runtime exists in draft **#7**, `feat/standalone-price-engine`,
head `46b33bf50773082b6d942816c676dd098ee6bad1`. Read its AGENTS.md,
DEVELOPMENT_STATUS.md and docs/API.md before producer development. That branch
contains the native UI, price ledger, sources, scheduling and public Python API v1.
No runtime changes are made here and no draft is merged.

EV companion #15 supplies public-API adapter/conformance tests. EV reconciliation
branch `feat/reconcile-price-api-v1`, code `1fb09e2`, combines that API approach with
#14 measured history. Local validation: **176 tests passed, zero skips, 91% coverage**,
Ruff/format passed, official hassfest 1 valid integration. Three actual producer
API/ledger tests use synthetic inputs across 92/96/100-quarter days and cover
stale readiness/site isolation. No live sources/hardware or invoice-file verification.

Checkpoint subject: `Mark service contract proposal superseded by producer API v1`.
This is documentation-only; diff whitespace validation passed. Producer runtime
suite was not rerun in this docs-only checkout. Producer #7/EV #15 remote CI was
previously green at the fetched heads. GitHub credentials expired during subsequent
EV push: Git could not read Username; API returned HTTP 401. Cannot publish this
correction, comment on drafts or check new remote CI until authentication is restored.

Next session: authenticate GitHub, push this docs branch, annotate producer #6 /
Issue #5 with authoritative draft #7. Push EV reconciliation branch and create a
separate draft on #14, then check exact-head tests/hassfest/HACS. Continue EV's
DEVELOPMENT_STATUS.md next task (deadline-scoped pricing) without duplicating ports.

All price business logic belongs to the producer. Household EWII 0.030 DKK/kWh
ex VAT for June–September 2026 remains scoped historical issue evidence only;
raw invoices absent. Never infer other sites/later contracts. No live commands,
Node-RED changes, merge, release, deployment or production cutover is authorized.
