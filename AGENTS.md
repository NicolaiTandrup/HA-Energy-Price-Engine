# HA Energy Price Engine continuation

Read docs/DEVELOPMENT_STATUS.md, relevant issues and open PRs, then inspect Git
state before editing. Reuse validated work; use the existing isolated checkout,
no worktree unless requested. Commit/test/push coherent checkpoints and update
that same handoff, with exact validation evidence and next steps.

This repository is the authoritative price producer. EV Charge Manager is a
read-only consumer; never import vehicle commands or duplicate tariff ownership
in its consumer. Preserve settled price history and read-time lookup-only behavior.
All unverifiable business settings belong in native HA config/options UI, not code.
Household invoices prove only their household/period; redact personal identifiers
and never infer another site's or a later supplier contract.

Keep Node-RED production untouched. No production HA changes, live charging commands,
merge, stable release or deployment without owner authorization. No secrets or raw
private invoices in commits. Ask only for meaningful design/compatibility/safety
choices; continue safe independent work while external prerequisites are missing.
