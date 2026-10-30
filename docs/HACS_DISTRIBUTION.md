# Install and update with HACS

Repository: **NicolaiTandrup/HA-Energy-Price-Engine**. Category: **Integration**.
Target: **v0.1.0-beta.9** (manifest `0.1.0-beta.9`). The
[public prerelease](https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases/tag/v0.1.0-beta.9)
is the installation source. The reproducible package and release receipt identify the exact immutable
source and checksums; a moving branch is not a release.

1. Take a full backup of your development Home Assistant. Tested cores are
   2026.10.3 and 2026.10.4. Cloud validation does not establish Raspberry Pi capacity.
2. **HACS → Custom repositories**: add
   `https://github.com/NicolaiTandrup/HA-Energy-Price-Engine`, category **Integration**.
3. Open Energy Price Engine in HACS. Persist **Show beta versions**, refresh
   repository information, select **v0.1.0-beta.9**, then Download.
4. Restart HA. HACS must show the installed semantic beta version. Device info must
   show manifest version **0.1.0-beta.9**. Reload the browser/app after restart so it loads the new fields and translations.
5. Configure the official Home Assistant **Nord Pool** integration with your actual
   area first. PE needs no additional credentials. A legacy custom component
   shadowing the official domain is rejected. Recorded legacy comparisons are
   offline; simultaneous live operation of both integrations is unnecessary.
6. New site: **Settings → Devices & services → Add integration → Energy Price
   Engine**. Upgrade: existing site's **Configure**; IDs, source mapping, dated
   contracts, overrides, entities, SQLite rows and revisions are preserved.
7. Follow the [three-stage guide](WIZARD_GUIDE.md). Confirm your supplier agreement
   or enter a custom markup in øre/kWh and its VAT basis. No dates are needed.
   Save and continue applies each page; Configure resumes after closing. Review
   needs no final save. Inspect raw/final coverage and a stored breakdown, then
   complete the [acceptance checklist](BETA_ACCEPTANCE.md), including restart and
   comparison of the marginal components from your agreement/bill. Close cannot submit fields still being typed.

8. Optional price dashboard: add the bundled local module to **Settings → Dashboards →
   Resources**, then paste [dashboard.yaml](dashboard.yaml) and replace one entity ID.
   Full [dashboard installation and tables/graphs guide](PRICE_DASHBOARD.md). No extra
   HACS frontend repository is required.

HACS uses compliant main for registration and the exact selected release tag for
installation. Beta distribution does not require merging development into main.
Manual installation: extract the manual ZIP into your HA configuration directory,
so `custom_components/ha_energy_price_engine/manifest.json` exists, then restart.
The smaller HACS-layout ZIP contains the integration files at its root; extract it
inside `custom_components/ha_energy_price_engine`, not over the configuration root.
Verify downloaded assets against SHA256SUMS before manual installation.

## Existing sites and beta.9 diagnostics

Keep your existing entries. Beta.8 source references, site IDs, dated rules/manual
rates, SQLite revisions and existing entities are retained. **Configure → Done –
return to integration** closes the saved review. On the device, inspect **Component
period**, eight individual numerical components, availability and the exact first
verified timestamp. New technical/unused estimate entities default off.

Previously enabled canonical entities remain enabled to preserve your choices.
For a cleaner existing device, open **Configure → Technical diagnostics**, keep
anything used by your automations/Recorder, deselect unused technical duplicates
and submit. This explicit selection does not stop the engine or CM API. Old IDs
and recorded history remain available; disabled rows stop recording new samples.
The ordinary status entities display localized Ready/Incomplete/Stale/Error;
advanced canonical machine enums retain their original uppercase states.

## Why a HACS card could show a commit hash

In HACS 2.0.5/current pinned upstream, an installed beta does not itself enable
Show beta versions. With no stable release and that setting off, HACS's available
version falls back to main's short commit. Selecting a beta download alone is not
the same as subscribing to beta updates. PE's `hide_default_branch` hides a branch
choice but cannot override HACS's update property.

PE provides **Configure → Final prices → Advanced settings → Storage / site management → HACS beta channel**, explicitly
approved by an administrator. It uses supported HACS repository WebSocket commands
against the same local HA socket, enables beta only for PE, refreshes and verifies
the semantic available version, then persists HACS's own repository state. It does
not patch HACS, disable an entity, download a package or alter another repository.
If the local authenticated request is unavailable, use HACS's Show beta versions
control and refresh information. Keep it enabled while testing betas.

The separate PE Published release entity also reads published semantic release
metadata, follows prereleases for installed betas, excludes them for stable users,
and never offers commit hashes. It directs installation through HACS.

## Branding

HA 2026.10 supports the bundled `brand/icon.png` through its native
`/api/brands/integration/ha_energy_price_engine/icon.png` route. Device/integration
surfaces and PE's release entity use supported local branding. The README includes
the same image.

HACS 2.0.5's own UpdateEntity still requests the external HA brands CDN. A bundled
icon cannot populate that separate catalog. Until the domain is accepted into
`home-assistant/brands`, that HACS-owned image may show a fallback. No global HACS
patch or fake CDN response is shipped. Catalog submission requires its maintainers'
review; see [contributor guidance](../CONTRIBUTING.md). This image limitation does
not change package installation or price verification.
