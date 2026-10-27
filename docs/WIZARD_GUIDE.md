# Configure Energy Price Engine beta.5

Upgrade through HACS and restart. On an existing site choose **Configure**; do not
delete/recreate it. Device info shows version from the installed manifest. Forms
follow the current user's English or Danish interface language; existing entity
names follow HA's system language and entity registry.

## Five ordinary stages

**Save and continue / Gem og fortsæt** saves the accepted page to the actual HA
configuration and updates pricing. The next page says **Saved / Gemt**. Close and
reopen Configure to resume. Review is already saved: no draft, final commit or
incomplete-finish form. Unsubmitted typing cannot be saved by closing HA's dialog.
Use the previous-page link to revisit settings. From review, accepted edits return
directly to review and keep the other completed components. Avoid simultaneous
editing of the same site.

1. **Site and source.** Name your site and choose an existing official Nord Pool
   entry. A sole supported area is automatic; ambiguous entries require an area
   on this same page. Danish source facts supply Copenhagen and the documented
   DKK/MWh ex-VAT input convention. No area proves your grid company. The default
   user display is øre/kWh; canonical API and original sensors remain DKK/kWh.
2. **Grid.** Confirm **Radius C** only if this is your actual product. Its adapter
   verifies authoritative dated time-of-use tariffs. Otherwise enter your verified
   current manual rate and VAT convention, or leave it missing. Advanced retains
   dated/hourly overrides. A failed source never becomes a zero tariff.
3. **Supplier agreement.** Freshly verified official **EWII Basis El** and **Plus
   El** offers appear when available. A public quote is not your private contract:
   confirm the actual agreement and VAT basis. If it differs, choose **Other EWII
   agreement** or **Other supplier / custom markup**. Enter **Supplier markup above
   spot price (øre/kWh)**, VAT inclusion and an optional monthly subscription.
   Ordinary setup has no date fields. Zero requires an explicit confirmed zero.
   Unknown is allowed and stays visibly missing. An explicitly approved estimate
   is visualization-only and cannot make the consumer API READY.
4. **Taxes and heating.** Danish official-source sites receive documented bounded
   national baselines: Energinet net .043 and system .072 DKK/kWh ex VAT during
   2026; electricity tax .008 during 2026–2027. VAT defaults to 25%. This is dated
   verified baseline data, not live legislation discovery. Later periods and other
   products need verified rules. Heating eligibility requires your actual
   registration, year and evidence; enabling it invents no discounted rate.
5. **Review prices.** Eight clickable component rows show rate, source and status.
   Monetary review amounts are **øre/kWh including VAT**; VAT is applied once.
   Dates appear once alongside raw and final coverage. Click a component to change
   it. **Check prices** forces verification. Final price → **Diagnostics** shows
   applied values, periods and corrective actions. Advanced is inside Diagnostics.

## Agreement timing and preservation

A newly confirmed current agreement starts at the **next complete 15-minute
quarter** and remains in effect until changed. Earlier unknown quarters are not
backfilled and settled records are not rewritten. The first day's verified range
may be partial even when all remaining prices are verified. A full-day API query
still requires all that day's quarters; future queries can use the complete active
range. The activation diagnostic states the start time. Tomorrow can remain missing
until Nord Pool publishes it.

Existing historical contracts and scheduled future date/hour overrides survive
ordinary edits. Advanced → Dated rates supports explicit scheduling. The documented
historical EWII household .030 DKK/kWh ex VAT is June–September 2026 only; it is not
an October, future or other-site default. A public offer refresh never changes
an already accepted private agreement.

EWII suggestions retain official URL, fetch time, content hash and a maximum 24h
fallback snapshot. If fresh verification fails or the snapshot expires, unavailable
offers are hidden and manual input remains. Never treat the documentation's example
quotes as permanent defaults. Official pages observed on October 27 list Basis
16.5øre/0DKK monthly and Plus6.5øre/29DKK monthly; their markup VAT convention is
not explicit, so setup asks you to confirm it from your agreement. Monthly fees
are tracked separately and excluded from marginal kWh scheduling prices.

## Diagnostics, estimates and recovery

Raw spot sensors/source coverage remain independent of final prices. Diagnostics
identify the missing component, affected period and settings action. For a stored
quarter use Diagnostics → Advanced → Storage / site tools → Inspect stored quarter;
this exposes canonical components, VAT, provenance and revisions. Downloadable
diagnostics redact private free-form source text. Negative spot prices remain
negative before additions; DST days require 92/96/100 quarters. Mandatory refreshes
remain 13:05, 13:20, 13:40, 23:59 and 00:01 local time.

Approved estimates are labelled **ESTIMATED / UNVERIFIED**, never enter verified
SQLite history, publish authoritative revisions or give CM READY prices. They still
require valid public components. Never use them for charging control.

## Remove or reset one site

Diagnostics → Advanced → Storage / site tools → **Remove / delete this site** lists
only the selected site's owned paths. Ordinary HA removal or **Remove with archive**
retains identified history and records `.storage/ha_energy_price_engine.archives`.
It is not silently attached to a new same-name site.

Permanent deletion requires typing the exact site ID and confirming. It stops
writers and clears that entry's configuration, SQLite, backups, setup progress and
owned registries. Interrupted cleanup stays stopped until safely retried. Another
site, external/full backups, older archives and HA's global recorder are preserved.
HACS uninstall removes program files and retains data.

If HACS shows a commit hash, see the [beta-channel repair](HACS_DISTRIBUTION.md).

## Native frontend examples and demonstration

These are real disposable HA 2026.10.4/frontend 20260930.5 screens with synthetic
Nord Pool/Radius boundaries and fictional private rates. They are software evidence;
your PAHA02-DEV acceptance remains separate. Only unrelated decorative brands were
mocked; PE's local native brand route was served normally.

| Journey | Evidence |
| --- | --- |
| English custom contract | [Markup](images/beta5/custom-markup-en.png), [saved/resumed](images/beta5/resumed-tax-en.png), [mobile review](images/beta5/review-en-mobile.png) |
| Danish EWII offer | [Products](images/beta5/products-da.png), [public quote and confirmation](images/beta5/ewii-quote-da.png), [desktop](images/beta5/review-da.png), [mobile](images/beta5/review-da-mobile.png) |
| Missing / provisional | [Missing supplier](images/beta5/missing-review-en-mobile.png), [estimate review](images/beta5/provisional-review-en-mobile.png), [diagnostics](images/beta5/provisional-diagnostics-en-mobile.png) |
| Complete first run | [English custom contract demo](demos/beta5-custom-first-run.webm), [Danish EWII Plus demo](demos/beta5-ewii-plus-da.webm) |

[Simulation receipt](receipts/v0.1.0-beta.5-simulation.json) ·
[Owner acceptance checklist](BETA_ACCEPTANCE.md)
