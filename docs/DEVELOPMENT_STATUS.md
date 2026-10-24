# Development handoff

Updated 2026-10-24. Active branch `docs/ev-consumer-contract-v1`, based on main.
This repository had README/LICENSE and requirements Issues #1–#5, no runtime or API.

Current checkpoint: proposed shared read-only consumer contract v1 under
`docs/contracts/price-consumer-v1.md`, coordinated with EV Charge Manager's new
`feat/authoritative-price-consumer` draft. Contract text is identical in both repos.
Do not mistake the proposal or consumer mock tests for producer implementation.

The producer owns all tariff/VAT/source/ledger/schedule business logic and native
editable pricing UI. EV's existing tested pricing modules are migration/reference
code that may be ported here under source/license provenance in a separate task.
No new permanent pricing work belongs inside EV Charge Manager.

Invoice scope from owner Issue #4: 0.030 DKK/kWh ex VAT household EWII markup in
June–September 2026 only. Raw invoice attachments are not in the current workspace;
no raw-file verification claimed. Do not publish addresses/customer identifiers or
apply this amount to other sites/later dates.

Validation: draft contract copied byte-identically across the two checkouts and
its synthetic example is exercised by EV's decoder tests. Producer runtime tests,
HA install, hassfest/HACS and actual API interoperability are unrun: there is no
producer implementation in this docs-only checkpoint.

Next: review/adopt contract with Issue #5 and EV consumer PR. Bootstrap the actual
native producer in a separate draft, reusing EV migration/reference algorithms and
tests where appropriate. Create native config/options flows for every unverifiable
component as specified in Issues #1/#4. Expose durable lookup without fetching or
calculating on reads, and revision events only for changed future final prices.
Before stopping update this file, commit/push and record actual results. No merge,
release, deployment or production cutover.
