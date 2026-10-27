# Configure marginal charging prices

Upgrade to beta.6 through HACS, restart HA and reload the browser/app. Existing
users choose **Configure** on the existing site. Device info must show manifest
version **0.1.0-beta.6**. Keep existing identities and history.

## Three ordinary stages

1. **Site and Nord Pool.** Name the site and select an installed official Nord Pool
   integration. A sole supported area is automatic; multiple areas need a choice.
   Danish source facts establish Copenhagen and DKK/MWh excluding-VAT input. These
   provider conventions are not editable display preferences. Ordinary setup shows
   no provider entity, attributes, technical IDs or unit-contract fields.
2. **Grid tariff.** Confirm **Radius C** only if it is your actual operator/product.
   DK1/DK2 alone cannot establish this. PE reads verified dated time-of-use rates
   and resolves every future quarter independently, including seasonal/midnight/DST
   changes. Other products need verified manual flat/hourly rules under Advanced.
   An unavailable automatic source does not turn into a zero or flat current tariff.
3. **Supplier markup.** Enter the actual supplement above spot in **øre/kWh** and
   its VAT basis. Examples: **0.25, 0.50, 0.75, 3.125**; Danish comma works too. Saving
   confirms your agreement and VAT choice. A zero needs an actual confirmed zero.
   Leave blank if unknown; existing saved rates are kept. No dates, subscription,
   product selection or heating question is required.

**Save and continue / Gem og fortsæt** applies each completed page. The markup page
uses **Save markup / Gem tillæg**. Close and reopen Configure to resume the last
accepted stage. Invalid values remain visible for correction. Review requires no
additional save. Tap any component to edit; accepted changes return to Review and
keep the other completed settings. Native forms have no dedicated per-page Back
button and cannot save typing that was never submitted.

New current values start at the **next complete 15-minute quarter**, until changed.
Earlier unknown quarters are not filled; settled prices are never rewritten.
Historical contracts and explicitly scheduled future date/hour overrides survive
ordinary edits. A new site's first day may have only remaining-day final coverage;
full-day consumer reads remain INCOMPLETE, while complete active future ranges can
be READY. The start time is shown. Tomorrow can remain unavailable before publication.

## Public charges and private agreements

Danish official-source sites receive bounded verified defaults: Energinet net
**4.3 øre**, system **7.2 øre** excluding VAT during 2026; electricity tax **0.8 øre**
excluding VAT during 2026–2027; VAT 25%. These are documented dated baselines, not live
legislation discovery or a promise of future rates. Expired/unavailable components
block final readiness and point to the relevant settings. Heating eligibility is
optional Advanced configuration and needs actual evidence and verified rates.

Optional public EWII offers are under Advanced. Fresh official quotes require your
actual agreement/VAT confirmation; they never silently replace a private contract.
A cached public snapshot expires within 24h. Current custom input works independently
of public-offer availability. Historical EWII household 0.030 DKK/kWh ex VAT applies
June–September 2026 only, never as a current/other-site default. Monthly subscription
metadata remains optional Advanced data and is excluded from every marginal price
and charging estimate.

## Read the calculation

Review's monetary amounts are **øre/kWh including VAT**. Raw spot readiness is
separate from final readiness. One **Check prices** action forces source verification.
Select **Final prices** to open component diagnostics. Choose another quarter to
inspect stored current/future amounts, sources, validity and verification. UTC offsets
distinguish repeated autumn DST hours; nonexistent spring quarters are not invented.
UI reads use canonical stored components and never retrieve/recompose verified prices.

The breakdown lists components **excluding VAT**, then their stored VAT and final
VAT-inclusive price. Selected future peak-quarter example from a disposable native HA simulation:

| Component | øre/kWh excluding VAT |
| --- | ---: |
| Spot |10.000000 |
| Radius C peak |95.557300 |
| Energinet net |4.300000 |
| Energinet system |7.200000 |
| Fictional confirmed supplier markup |0.500000 |
| Electricity tax |0.800000 |
| Subtotal |118.357300 |
| VAT |29.589325 |
| **Final including VAT** |**147.946625** |

A separate current-quarter example, with 0.25 øre **including VAT** supplier markup,
resolves 54.3524 øre subtotal + 13.5881 øre VAT = **67.9405 øre/kWh**.

This combines **synthetic 100 DKK/MWh spot**, recorded public Radius data and a
fictional private agreement. It is not a live market quote or your contract. The
following normal-band quarter is 68.3155 øre including VAT. Each uses its own stored
grid rate. Missing or stale prices never become free electricity. Negative spot
prices are preserved; the final price includes applicable additions.

Explicitly approved estimates are available under **Advanced → Provisional
visualization estimate**. They use separate transient canonical components and
are labelled Provisional. They never enter verified SQLite rows/revisions or make
CM READY. Old retained ledger values remain intact, even when a different estimate
is visualized. Missing/stale public components block final estimates too.

## Estimate a charging session

Diagnostics → **Charging cost estimate** takes a first quarter, one kWh amount per
consecutive quarter and **Planned** or **Measured** energy. A point/comma is accepted.
For example, enter 1.25 on the first line and 2.0 on the next. Explicit zero-energy
quarters are allowed; missing quarters or measurements are not assumed zero.
Future energy must be planned. The calculator uses verified API v1 prices and shows
an estimate, even for measured energy; it does not settle an account or create a
charging plan. CM remains responsible for session measurement/planning/control.

In the example above, 1.25 kWh in the peak quarter and 2.0 kWh in the following normal
quarter cost **3.2156428125 DKK**, displayed 3.2156 DKK. Fixed fees are excluded. A missing,
stale or provisional price makes the estimate unavailable. Supplied allocations
are not persisted as an energy ledger or sent as charging commands.

## Advanced, recovery and safe reset

Diagnostics → **Advanced** retains dated rates/overrides, public supplier offers,
heating eligibility, display preferences, explicit alternate source contracts and
storage/site tools. Official Nord Pool mode hides entity-only fields; choosing an
alternate source redraws those fields and requires a complete verified contract.
Preferred display is øre/kWh; original entities and API v1 remain DKK/kWh including VAT.
Forms follow the current English/British-English/Danish user language. Existing
entity names follow HA's system language and registry.

Storage/site tools provide backups and a stored-quarter technical view. Ordinary
removal retains an identified history archive. Permanent selected-site deletion
requires its exact ID and confirmation, stops writers and removes only that entry's
owned config/history/cache/setup/registry data. Another site, external backups and
HA's recorder are preserved. HACS uninstall removes software and retains data.

[HACS update/repair](HACS_DISTRIBUTION.md) · [Recovery](ADR-002-ledger-storage.md) ·
[Owner acceptance](BETA_ACCEPTANCE.md)

## Native frontend evidence

Real disposable HA 2026.10.4/frontend 20260930.5 with recorded/synthetic provider
boundaries, not owner acceptance. Native PE branding was served normally; only
unrelated decorative brands were mocked. Browser plugin unavailable; Playwright/
system Chromium used. Desktop 1440×1000 and mobile 390×844.

| Case | Evidence |
| --- | --- |
| Source/grid | [Source](images/beta6/site-enGB.png), [Radius](images/beta6/grid-enGB.png) |
| Fractional agreement | [Saved input](images/beta6/saved-markup-mobile-enGB.png), [Danish comma](images/beta6/markup-da-mobile.png) |
| Prices | [English review](images/beta6/review-mobile-enGB.png), [Danish](images/beta6/review-da-mobile.png) |
| Canonical calculation | [Current](images/beta6/current-quarter-mobile-enGB.png), [future quarter](images/beta6/verified-quarter-mobile-enGB.png) |
| Session estimate | [Allocated energy](images/beta6/cost-estimate-mobile-enGB.png) |
| Incomplete/estimated | [Missing](images/beta6/missing-review-mobile-en.png), [provisional](images/beta6/provisional-review-da-mobile.png), [future components](images/beta6/provisional-future-mobile-en.png) |
| Source errors/recovery | [Official mode](images/beta6/official-source-fields-en.png), [timezone](images/beta6/invalid-timezone-en.png), [outage](images/beta6/outage-review-en.png), [recovered](images/beta6/recovered-review-en.png) |
| Safe reset | [Confirmation](images/beta6/delete-confirmation-error-en.png), [new empty agreement](images/beta6/recreated-empty-supplier-en.png) |
| Old resource compatibility | [Description](images/beta6/legacy-description-compat-enGB.png), [named menu](images/beta6/legacy-menu-compat-enGB.png) |

[Simulation and migration receipt](receipts/v0.1.0-beta.6-simulation.json)
