# First setup

Install beta.5 using the [exact HACS procedure](HACS_DISTRIBUTION.md), restart HA,
and follow the [illustrated native setup](WIZARD_GUIDE.md). Existing installations
use Configure on their existing site. Back up first. Tested cores: 2026.10.3/.4;
cloud validation does not establish Raspberry Pi performance.

You need your installed **official Nord Pool** entry, actual area/grid product and
supplier agreement (markup, VAT convention and optional monthly subscription).
Ordinary setup needs no dates. Public EWII suggestions require agreement confirmation;
custom rates never assume a private contract. National defaults are bounded dated
baselines, not an automatic promise of future rates or heating eligibility.

Five stages: site/source → grid → supplier → taxes → review. **Save and continue**
applies each accepted page. Close/reopen Configure to resume the next stage. Review
needs no final save. Click any component for correction; use Check prices for a
fresh verification. Raw coverage and final readiness are separate.

A new current agreement starts at the next complete quarter, open-ended until
changed. No earlier unknown price is filled and no settled row is rewritten.
The first day can have only remaining-day final coverage; full-day consumer reads
remain INCOMPLETE until full coverage exists. Missing values never become zero.
Estimates require explicit approval, remain separate from ledger/API READY and
must never control charging. Monthly subscriptions are excluded from marginal prices.

One entry is one independently configurable site. Upgrading preserves IDs, mappings,
entities, advanced dated rules, SQLite rows and revisions. Canonical stored/API prices
remain DKK/kWh including VAT; ordinary review defaults to øre/kWh including VAT.
Inspect a stored breakdown, restart, compare with your bill and complete the
[owner acceptance checklist](BETA_ACCEPTANCE.md). Your credentials, providers,
invoice and actual hardware are not certified by synthetic software tests.
