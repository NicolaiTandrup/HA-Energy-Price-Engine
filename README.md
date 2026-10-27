# Energy Price Engine for Home Assistant

![Energy Price Engine](custom_components/ha_energy_price_engine/brand/icon.png)

Verified **15-minute marginal electricity prices** for EV charging optimization and
estimated charging costs. Prices include spot, grid time-of-use tariffs, supplier
markup, Energinet charges, electricity tax and VAT. Fixed subscriptions are excluded.
Each pricing site has independent settings and persistent SQLite history.

**v0.1.0-beta.6** · [Prereleases](https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases)

## Install or upgrade

1. Add `https://github.com/NicolaiTandrup/HA-Energy-Price-Engine` to **HACS → Custom
   repositories**, category **Integration**.
2. Open Energy Price Engine, persist **Show beta versions**, refresh information,
   choose **v0.1.0-beta.6**, download and restart Home Assistant. Reload the browser/app.
3. Existing sites: choose **Configure** on the existing entry. New sites: install
   Home Assistant's **official Nord Pool** integration first, then **Settings →
   Devices & services → Add integration → Energy Price Engine**.

[Exact HACS procedure](docs/HACS_DISTRIBUTION.md) · [Setup and screenshots](docs/WIZARD_GUIDE.md)

## Three setup stages

1. Name the site and select its installed Nord Pool source/area.
2. Confirm the actual grid product: automatic **Radius C**, or a verified manual rate.
3. Enter your actual supplier markup in **øre/kWh** and its VAT basis.

Fractional amounts such as **0.25**, **0.50**, **0.75** and **3.125** work, including
Danish decimal commas. Ordinary setup needs no dates, subscriptions, product choice
or heating eligibility. Verified Danish national defaults apply within documented
periods. Private agreements and grid classes are never inferred from DK1/DK2.

Each accepted page saves immediately. Close and reopen Configure to resume.
Review needs no final save; tap a component to edit and use **Check prices** to
verify sources. New rates start at the next complete quarter without rewriting
settled history or filling earlier unknown prices.

## Understand and use prices

Final prices opens current/future quarter diagnostics: actual stored component
amounts, sources, periods and verification, with VAT applied once. An optional
charging-cost calculator uses **supplied quarter-hour kWh allocations**, labelled
planned or measured. It does not create a charging plan, discover energy usage or
reconstruct a household bill. CM owns vehicles, sessions, planning and control.

Unknown rates never become zero. Raw spot prices remain visible independently.
Explicitly approved visualization estimates stay **Provisional**, outside verified
history and API READY; they cannot provide authoritative prices or session costs.

The [read-only API v1](docs/API.md) and canonical entities remain **DKK/kWh including
VAT**. Normal display is **øre/kWh**. Upgrades preserve site IDs, source mappings,
entities, dated rules and SQLite rows/revisions. Advanced retains manual contracts,
dated overrides, display settings and controlled site removal/reset.

[Owner acceptance](docs/BETA_ACCEPTANCE.md) · [Storage/recovery](docs/ADR-002-ledger-storage.md) ·
[Performance limits](docs/PERFORMANCE.md) · [Contributing/provenance](CONTRIBUTING.md) · [License](LICENSE)
