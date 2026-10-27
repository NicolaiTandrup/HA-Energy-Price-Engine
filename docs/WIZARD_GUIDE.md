# Configure and understand charging prices

Install **v0.1.0-beta.7** through HACS, restart HA and reload the browser/app.
Existing users choose **Configure** on their existing site. Device info must show
manifest version **0.1.0-beta.7**. Site identities, entities, source mappings, dated
rules, SQLite history and original revisions remain.

## Three setup stages

1. **Site and official Nord Pool.** Select an installed official integration and
   actual area. A sole supported area is automatic. Provider input conventions
   (Danish DKK/MWh excluding VAT, Copenhagen) are detected; no entity, attribute,
   technical ID or editable provider-unit contract is required here.
2. **Grid tariff.** Confirm automatic **Radius C** only if it is your actual product.
   DK1/DK2 cannot establish a private grid class. Each quarter resolves its own
   recorded time-of-use/date/version. Other products need verified manual rates.
3. **Supplier markup.** Enter the actual **øre/kWh** supplement and VAT basis.
   Point/comma fractions such as **0.25, 0.50, 0.75, 3.125** retain their exact input
   precision. Saving confirms your agreement. Blank keeps an existing agreement;
   unknown is never silently zero. No dates, monthly fees, product or heating choice
   is mandatory. Contract input units are explicitly labelled, independent of display.

Each accepted page saves immediately. Close/reopen resumes. Review requires no final
save; tap a component to edit. **Check prices** forces source verification. Native
forms cannot save typing that was never submitted and have no per-page Back button.
New current terms begin next complete quarter, until changed. Settled prices,
historical terms and scheduled future date/hour overrides survive ordinary edits.

## One preferred price unit

All preferred raw spot/current/next/final/statistic/provisional price entities and
native monetary breakdowns use **øre/kWh, exactly 2 decimal places** by default.
Advanced → Display unit optionally selects **DKK/kWh, exactly 4 places**. Forms use
English/British-English/Danish and the user's HA number-format preference, including
point/comma overrides and supported browser-system decimal conventions. VAT
percentages are not per-kWh prices. Missing amounts show a dash, never a numeric zero.

Raw preferred entities explicitly identify their input VAT basis. Final preferred
entities include VAT. Review's component checklist shows VAT-inclusive amounts;
Detailed diagnostics show components excluding VAT, a subtotal, VAT amount and final
inclusive total, with actual source/period/verification. Rounding is presentation
only. Rounded components/subtotals can differ in their last digit from the rounded
final total; calculations and charging costs always use the unrounded stored values.

Canonical technical sensors retain **DKK/kWh**, stable IDs, complete numeric values
and measurement/statistics units. They are labelled technical and grouped as
diagnostics. Their supported presentation precision is four, while their recorded
values and API retain full precision. Preferred display entities have fixed unit
identities and no statistics state class. Switching units leaves the previous unit's
presentation entities unavailable, preserving history; use the currently selected
unit's entities. Explicit HA entity/card precision overrides can supersede integration
suggestions: reset those to Default, or choose 2/4, to use the standard presentation.

## Readiness is a range, not a promise about missing history

Review and diagnostics distinguish:

- **Current quarter**: one verified stored final interval.
- **Next quarter**: its own interval, including the first interval after midnight.
- **Requested future window**: every requested interval must exist and be verified.
- **Today's historical full day**: all 92/96/100 quarters, including earlier history.
- **Tomorrow's full day**: complete published and verified coverage, when available.

A site activated at 22:15 CET can correctly show **7/96 history INCOMPLETE**, current
and next **READY**, tomorrow **96/96 READY**, and a requested 22:15–00:30 window
**9/9 READY**. Earlier unknown quarters are intentionally not backfilled. Historical
incompleteness does not invalidate a fully priced future window. Missing future
quarters, failed sources/components, stale verification and provisional estimates
still prevent READY. No future price is assumed zero.

Use **Check future window**, directly from Review or Final prices. Select start and
end; the end boundary is excluded. The picker shows the next 48 actual hours,
including calendar boundaries where prices may not yet exist. UTC offsets distinguish
repeated DST hours. This picker limit is not an API limit or a charging plan. The
check changes no configuration; CM submits its own exact quarter-aligned range to
unchanged read-only API v1. A window across an unpublished date remains INCOMPLETE.

## Current and next-quarter example

This reproducible simulation uses synthetic **100 DKK/MWh spot**, recorded public
Radius C winter rates and a **fictional confirmed 0.50 øre/kWh excluding-VAT** supplier
markup. It is not a live quote or your private agreement. Frozen local time is
27 October 2026, 16:50 CET: current quarter 16:45, next quarter 17:00 peak.

| Component (øre/kWh excluding VAT) | Current 16:45 | Next 17:00 |
| --- | ---: | ---: |
| Nord Pool | 10.00 | 10.00 |
| Radius C | 31.85 | 95.56 |
| Energinet network | 4.30 | 4.30 |
| Energinet system | 7.20 | 7.20 |
| Supplier | 0.50 | 0.50 |
| Electricity tax | 0.80 | 0.80 |
| Subtotal | 54.65 | 118.36 |
| VAT amount | 13.66 | 29.59 |
| **Final including VAT** | **68.32** | **147.95** |

Optional DKK/kWh display: **0.6832 → 1.4795**. Canonical technical API values remain
**0.683155 → 1.47946625 DKK/kWh**. Each quarter uses its own stored tariff. No UI read
fetches Nord Pool/Radius or recomposes a verified electricity price.

Diagnostics → Charging cost estimate accepts explicitly supplied kWh per consecutive
quarter and Planned or Measured energy. Future measured energy is rejected. In this
example, planned **1.25/2.0 kWh** costs **3.81287625 DKK**, displayed **3.8129 DKK**;
using rounded display prices would be wrong. Missing/stale/provisional prices make
this estimate unavailable. PE invents no energy, session or charging plan; CM owns
those responsibilities. Fixed subscriptions are excluded, and this is not accounting.

## Verification, storage and recovery

Danish public defaults remain bounded verified baselines: 2026 Energinet net 4.3/system 7.2
øre excluding VAT, 2026–2027 tax 0.8 øre,25% VAT. Expired periods need verified rules;
this is not live legislation discovery. Private agreements/heating eligibility are
never guessed. Optional public EWII offers remain Advanced and require actual agreement/
VAT confirmation. Historical household 0.030 DKK exVAT applies June–September2026 only,
not a current/other-site default. Fixed subscriptions never enter marginal prices.

Price calculation happens on verified input refresh. SQLite stores UTC start/end,
final DKK/kWh, applied component amounts (including original spot normalized once),
source/input convention/verification and revisions. Startup checks and loads those
rows into an immutable sorted memory index. API reads use indexed range slices with
no network, composition, SQLite connection or writes. Offline SQLite range queries
also use the existing primary-key index. Changed future records alone are replaced;
settled and unchanged records retain their values and revisions. No schema rewrite.

Provisional visualization prices remain separate transient records, explicitly labelled
unverified. They never enter verified SQLite rows/revisions or make CM API READY.
Advanced retains dated rules, display, source contracts, optional heating and storage/
site tools. HACS uninstall retains data. Permanent selected-site deletion requires
exact ID and confirmation; other sites, external backups and HA recorder are preserved.

[HACS procedure](HACS_DISTRIBUTION.md) · [Acceptance checklist](BETA_ACCEPTANCE.md) ·
[Storage/recovery](ADR-002-ledger-storage.md) · [Performance limits](PERFORMANCE.md)

## Reproducible validation

[Price/locale/registry tests](../tests/test_beta7_presentation.py) ·
[Late activation, indexed reads, midnight/DST and current/next tests](../tests/test_beta7_readiness.py) ·
[Native HA simulation receipt](receipts/v0.1.0-beta.7-simulation.json).

Native QA uses isolated HA 2026.10.4/frontend 20260930.5, desktop 1440×1000/mobile 390×844,
EN/en-GB/DA with synthetic/recorded provider boundaries. Browser plugin unavailable;
existing Playwright/system Chromium used. Native PE branding loads normally; only
unrelated decorative brands are mocked. This is software evidence, not owner acceptance.
Actual private terms, provider availability, physical mobile experience and Pi
capacity/recovery remain owner-run checks. Cloud benchmarks do not establish Pi speed.
