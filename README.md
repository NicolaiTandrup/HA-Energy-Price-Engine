# Energy Price Engine for Home Assistant

![Energy Price Engine](custom_components/ha_energy_price_engine/brand/icon.png)

Electricity prices for your home, including spot price, grid tariff, supplier
markup, national charges and VAT. Energy Price Engine stores verified 15-minute
prices in Home Assistant and supports independently configured sites.

**v0.1.0-beta.5.** Use the published version shown on the
[releases page](https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases).
Beta software requires your own bill, tariff and restart acceptance checks.

## Install with HACS

1. In **HACS → Custom repositories**, add
   `https://github.com/NicolaiTandrup/HA-Energy-Price-Engine` as **Integration**.
2. Open Energy Price Engine in HACS, enable **Show beta versions**, refresh its
   information and select **v0.1.0-beta.5**. Download and restart HA.
3. Open **Settings → Devices & services → Add integration → Energy Price Engine**.
   Existing users choose **Configure** on their existing site to preserve history.

[Installation and updates](docs/HACS_DISTRIBUTION.md) ·
[Step-by-step setup](docs/WIZARD_GUIDE.md) ·
[Acceptance checklist](docs/BETA_ACCEPTANCE.md)

## Complete your pricing

The native setup has five stages: site/source, grid, supplier agreement, taxes,
and a numerical review. Install Home Assistant's **official Nord Pool integration**
first. Its DKK/MWh excluding-VAT input convention is detected independently of the
preferred **øre/kWh** display.

Confirm Radius C only if it is your actual grid product. Verified Danish national
baselines apply within their documented periods. Select a freshly verified public
EWII offer and confirm your actual agreement, or enter your own **supplier markup
in øre/kWh**, VAT convention and optional monthly fee. Ordinary setup needs no dates.
Monthly fees remain separate from marginal prices. Private terms and heating
eligibility are never guessed.

**Save and continue** applies each accepted step immediately. Close and reopen
Configure to resume; there is no final draft commit. The compact review shows each
component's rate, source and status, with direct settings links and one **Check
prices** action. Unknown components never become zero. New current agreements
start at the next complete quarter without backfilling earlier unknown prices.

You may explicitly approve a provisional supplier amount for **ESTIMATED /
UNVERIFIED visualization only**. These sensors are separate from verified history
and the read-only consumer API. Never use estimate sensors for charging control.

## Keep control of your data

Submit each page before closing: Home Assistant cannot save unsubmitted keystrokes.
Use final price → Diagnostics → Advanced for dated overrides, display, backups
and site management. Ordinary removal retains an identified history archive.
Permanent selected-site cleanup requires explicit confirmation. HACS upgrades and
uninstalls preserve history; upgrades retain existing IDs, mappings and entities.

The integration provides prices and a [read-only API](docs/API.md). It contains no
vehicle, charger or heating controls. Public components are verified independently
of your private contract. English and Danish wizard text follows your HA interface
language. Existing entity names follow HA's registry and system-language rules.

[Storage and recovery](docs/ADR-002-ledger-storage.md) ·
[Performance limits](docs/PERFORMANCE.md) ·
[Contributing and implementation provenance](CONTRIBUTING.md) · [License](LICENSE)
