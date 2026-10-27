# Configure Energy Price Engine

Update through HACS and restart Home Assistant. Existing beta users choose
**Devices & services → Energy Price Engine → Configure** on their existing site;
do not delete/recreate it to upgrade. Device info derives the software version from
the installed manifest. A new site gets its own stable ID and independent history.

## Six stages

Choose Next, Back or Review, then **Continue / Fortsæt**. Continue preserves the page
as a durable draft; **Save & verify** applies it. Closing cannot submit typed fields:
press Continue first. Invalid submissions and Back edits remain resumable. Advanced
contains an explicitly confirmed draft-discard action. Avoid simultaneous editing
flows for one site.

1. **Site and Nord Pool source.** Enter a friendly name; leave the optional ID blank
   for an automatically assigned stable ID. Select your installed official Nord
   Pool entry by name. Confirm its supported area; DK1 is not DK2. Copenhagen is
   suggested for a verified Danish area. Official input is DKK/MWh excluding VAT;
   it is independent of your display choice. Enter **25** for 25% VAT. Advanced
   entity providers expose their own unit and verification settings.
2. **Grid tariffs.** Choose automatic Radius C only if this is your actual tariff
   product. Area alone cannot prove your grid company or class. The adapter reads
   authoritative dated grid rates and checks coverage. Other products require
   verified dated manual rules under Advanced. No missing tariff becomes zero.
3. **Electricity supplier.** Select EWII or another supplier as a label. Answer:
   **What is your supplier markup above the spot price?** Find the per-kWh trading
   fee or spot supplement in your electricity bill/contract. Exclude fixed monthly
   subscriptions. Enter the amount, preferably in **øre/kWh**, VAT inclusion and
   the actual effective dates. A period through September 30 has exclusive end
   October 1. Confirm that you checked your bill/contract. A zero markup needs an
   explicit zero in that document. No amount is prefilled. The old EWII household
   .030 DKK/kWh excluding VAT applies June–September 2026 only, never current terms.
   Existing saved periods can be retained; explicit overlap replacement preserves
   dates outside the replacement interval. Advanced shows each stored period.
   If the value is unknown, select **I do not know my markup yet**, or explicitly
   approve a **provisional visualization-only estimate**. An estimate is
   ESTIMATED/UNVERIFIED; it does not enter verified history, make the API READY or
   enable charging. Estimates still require fresh public components.
4. **National charges and taxes.** New Danish official-source sites suggest a
   visible documented bounded baseline: 2026 Energinet network .043 and system
   .072 DKK/kWh excluding VAT; 2026–2027 electricity tax .008. This is dated data,
   not live legislative discovery. Beyond those periods configure verified rates.
   Locked dated overrides remain available. Heating registration alone creates no
   discount; eligible rates need verified registration, evidence/year and usage.
5. **Display preferences.** Preferred display defaults to **øre/kWh**. Example:
   100 DKK/MWh input = .100 DKK/kWh = 10 øre/kWh before additions. Original DKK
   sensors, SQLite and consumer API remain canonical DKK/kWh.
6. **Review, Save & verify.** One Today/Tomorrow table compares all required
   components and final prices. Verified, Missing, Expired, Provisional and
   Unavailable statuses explain the next action. Missing components have direct
   correction choices. Advanced contains all steps, manual editing and diagnostics.
   **Save & verify** applies once, reloads and checks actual persisted verified
   prices for today. If unavailable, a **Saved – verified prices still unavailable**
   form offers corrections or intentional incomplete completion; this is not
   successful complete pricing. Tomorrow may remain unavailable before publication.

English/Danish forms, validation and selectors follow the authenticated user's HA
interface language. Entity names use HA's system language and existing registry;
changing a profile does not rename globally shared entities.

## Check prices and diagnose

Raw current/next-quarter spot sensors and source coverage work independently of
final prices. Final status and pricing-problem entities identify missing components,
affected dates, stale source/grid data or storage failures. Advanced → Inspect stored
quarter shows the actual VAT, sources, component periods and revision. Original
uppercase readiness/API values are preserved alongside localized diagnostic enums.

Do not interpret retained historical records as newly verified READY prices.
Negative spot prices remain negative before additions; 92/100-quarter DST days
need their actual local-day coverage. Automatic checks retain 13:05, 13:20, 13:40,
23:59 and 00:01 schedules. Test public source availability and your bill yourself.

## Remove, archive or start clean

Advanced → **Remove / delete this site** lists the selected entry's PE-owned paths.
**Remove with archive** retains identified history at those paths and records it in
`.storage/ha_energy_price_engine.archives`. It never autoattaches to a new site.
HA's ordinary integration Delete action also retains this archive.

**Permanent deletion** requires typing the selected site ID and confirming the
checkbox. It stops pricing/writers before clearing that active entry's SQLite,
backups, configuration audit, caches, submitted drafts and owned registry entries.
An interrupted cleanup stays stopped; Configure and retry after resolving access.
A new same-name site starts with a new entry ID and empty history. Earlier removed
archives, external/full backups and HA's global recorder history are separate;
this action does not delete them or another site's data. Integration-owned ID-only
cleanup markers contain no contract/history. HACS uninstall only removes program
files and preserves data.

If an update card shows a short commit hash, use Advanced → **Repair HACS beta
channel**, explicitly approve, then inspect HACS again. This uses HACS's supported
repository commands only for PE and persists Show beta versions. It installs
nothing. Administrator/local authenticated HTTP access is required; otherwise use
HACS's own Show beta versions control and refresh information.
