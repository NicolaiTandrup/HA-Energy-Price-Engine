# Energy Price Engine for Home Assistant

![Energy Price Engine](custom_components/ha_energy_price_engine/brand/icon.png)

Electricity prices for your home, including spot price, grid tariff, supplier
markup, national charges and VAT. Energy Price Engine stores verified 15-minute
prices in Home Assistant and supports independently configured sites.

**Beta.4 candidate.** Use the published version shown on the
[releases page](https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases).
Beta software requires your own bill, tariff and restart acceptance checks.

## Install with HACS

1. In **HACS → Custom repositories**, add
   `https://github.com/NicolaiTandrup/HA-Energy-Price-Engine` as **Integration**.
2. Open Energy Price Engine in HACS, enable **Show beta versions**, refresh its
   information and select **v0.1.0-beta.4** once published. Download and restart HA.
3. Open **Settings → Devices & services → Add integration → Energy Price Engine**.
   Existing users choose **Configure** on their existing site to preserve history.

[Installation and updates](docs/HACS_DISTRIBUTION.md) ·
[Step-by-step setup](docs/WIZARD_GUIDE.md) ·
[Acceptance checklist](docs/BETA_ACCEPTANCE.md)

## Complete your pricing

The six-stage native wizard guides you through source, grid, supplier, national
charges, display and review. Install and configure Home Assistant's **official
Nord Pool integration** first. PE uses its fixed DKK/MWh excluding-VAT convention.

Automatic Radius C is available when that is your actual grid product. Dated Danish
national baselines are restricted to their documented periods. Other products and
periods need verified dated rates. No private supplier rate or heating eligibility
is guessed. Tell the wizard your supplier's **per-kWh markup**, preferably in
**øre/kWh**, using your bill or contract, its VAT convention and effective dates.
Fixed monthly subscriptions do not belong in a marginal per-kWh price.

Review compares Today and Tomorrow and links directly to missing components.
**Save & verify** applies your draft and checks actual persisted prices. Missing,
expired or unavailable data never becomes a free or verified price. Raw spot prices
remain visible while you complete the other components.

You may explicitly approve a provisional supplier amount for **ESTIMATED /
UNVERIFIED visualization only**. These sensors are separate from verified history
and the read-only consumer API. Never use estimate sensors for charging control.

## Keep control of your data

Continue preserves submitted wizard pages as a resumable draft. Press Continue
before closing; Home Assistant cannot submit keystrokes from a closed dialog.
Use Advanced for dated overrides, stored breakdowns, backups and site management.
Ordinary removal retains an identified history archive. Permanent selected-site
cleanup requires explicit confirmation. HACS upgrades/uninstalls preserve history.

The integration provides prices and a [read-only API](docs/API.md). It contains no
vehicle, charger or heating controls. Public components are verified independently
of your private contract. English and Danish wizard text follows your HA interface
language. Existing entity names follow HA's registry and system-language rules.

[Storage and recovery](docs/ADR-002-ledger-storage.md) ·
[Performance limits](docs/PERFORMANCE.md) ·
[Contributing and implementation provenance](CONTRIBUTING.md) · [License](LICENSE)
