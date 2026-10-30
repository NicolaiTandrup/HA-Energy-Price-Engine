# Price dashboard (beta.8)

The bundled Energy Price Engine card shows both complete local days as 15-minute
series: **Nord Pool spot excluding VAT/charges** and **verified final electricity
price including VAT/variable charges**. It also includes today's applied network
tariff ranges, all quarter-hour components, and current/next/history readiness.
Default dashboard amounts are **øre/kWh, two decimal places**, regardless of the
site's optional entity display preference. The CM API and ledger stay full-precision
DKK/kWh. No subscriptions are added to marginal costs.

## Install once, without Python or SQLite

1. HACS → Energy Price Engine → enable **Show beta versions**, select
   **v0.1.0-beta.8**, Download. Restart Home Assistant and reload the browser/app.
   Device info should show **0.1.0-beta.8**. Configure your existing site normally.
2. Enable **Advanced mode** in your HA user profile. Open **Settings → Dashboards →
   three-dot menu → Resources**. Add this resource as **JavaScript module**:
   `/ha_energy_price_engine/energy-price-engine-card.js?v=0.1.0-beta.8`.
   This file is installed by the integration's HACS ZIP; no separate frontend
   repository, external service, or chart-library installation is needed.
   Keep one resource entry. On later updates change its version query and reload.
3. Create a new empty dashboard in **Settings → Dashboards**, open it, choose
   **Edit dashboard → three-dot menu → Raw configuration editor**. Paste the
   complete YAML below. Replace its **one entity ID** with any sensor of the desired
   PE site (copy it from that device's entity page, e.g. **Final now (incl. VAT)**).
4. Save and open the dashboard from the sidebar. Repeat the view/card with another
   site's entity for additional sites. Use a dedicated dashboard; replacing the raw
   configuration of an existing dashboard replaces that dashboard's layout.

```yaml
title: Energy prices
views:
  - title: Electricity prices
    path: electricity-prices
    icon: mdi:chart-timeline-variant
    type: panel
    cards:
      - type: custom:energy-price-engine-card
        entity: sensor.your_site_final_now_incl_vat
```

The identical ready-to-paste file is [dashboard.yaml](dashboard.yaml). For an
existing view, add only the `type`/`entity` card block. YAML-mode HA installations
must instead put the same module URL under `lovelace.resources` in
`configuration.yaml`; dashboard raw YAML does not define resources. Resource
registration is a deliberate supported HA UI step, not automatic injection into
HA's device page. No integration can insert arbitrary Lovelace graphs in the
standard device-details screen. Keep the normal device UI concise and pin this
price dashboard to the sidebar.

## Reading the dashboard

- The two graphs share a UTC-continuous local-calendar axis, a visible **Now**
  marker, and a today/tomorrow boundary. Each bar is one quarter. Negative values
  extend below zero; missing/unverified/stale final prices are **gaps**, not zero.
- Select a bar, choose a quarter in **Inspect a quarter**, or select a time in the
  complete schedule. The inspector shows raw spot, applied DSO, Energinet network
  and system, supplier markup, tax, VAT amount, final price, units, verification,
  source/effective dates, UTC identity and the stored price revision. Non-final
  amounts exclude VAT; VAT is a separate amount; final includes VAT once.
- **Today's network tariffs** merges adjacent exact equal applied stored DSO rates
  with equal verification/source. It covers **only today**, including explicit gaps.
  It is neither a seasonal catalogue nor an inferred tariff plan. A missing final
  ledger record cannot prove an applied DSO rate: that interval stays unavailable,
  even when an independent tariff source may contain candidate rates.
- **Every quarter-hour** contains every interval of both days (expand tomorrow),
  including unavailable rows. All rows remain visible in horizontally/vertically
  scrollable tables on phones; no hundreds of entities or large Recorder attributes.
  UTC offsets distinguish repeated autumn hours. Local days have 92/96/100 slots;
  skipped spring hours are absent. Start is inclusive, end exclusive.
- Current/next readiness is independent of historical full-day gaps. A late setup
  can show **Ready** for current/next while today's history is **Incomplete**.
  Tomorrow may await publication. The reason, missing components, corrective action
  and next scheduled check stay visible; no failed verification is relabelled Ready.
- A raw source can be valid when a supplier/grid/tax period is missing: the raw graph
  remains available and the final graph stays empty for those periods. Optional
  provisional prices never appear as verified data here. Retained stale final
  amounts are labelled in the inspector and are never plotted as Ready.
- Amounts are independently rounded only for display. Component rows may differ
  by 0.01 from their rounded total; unrounded stored values remain authoritative.
  English/British-English and Danish UI/number preferences are supported.

The card refreshes from HA state updates and at least once per minute, plus manual
**Refresh**. Verified future revisions appear without a browser reload. Reads use
HA's authenticated WebSocket and the in-memory indexed ledger; they never fetch a
provider, query SQLite, recompose tariffs, or write price/configuration data. No
new producer write action/service or charging control exists.

## Supported interfaces and limits

The integration registers the read-only command
`ha_energy_price_engine/price_schedule` with required `entity_id` using HA's native
WebSocket command API. It checks the authenticated user's HA read permission and
resolves that entity to its loaded PE site. The response is limited to today and
tomorrow; arbitrary date/SQL/export parameters are rejected. No site caps or
cross-site bulk payloads. `schema_version: 1` describes this presentation transport;
**it does not change the canonical CM Python API v1**.

Each response contains day/UTC boundaries, explicit-null quarter values in ore/kWh,
local offset timestamps, status/reason, revision, deduplicated applied source and
component snapshots, today's DSO ranges and readiness/check times. Raw values
normally come from stored applied spot; where final composition failed, independently
fresh normalized raw source slots can fill the raw-only series. An existing
record's original spot is never replaced by a newer source in its breakdown.
Full all-in entity inputs cannot reveal an unknown component split: raw/components
stay unavailable rather than being inferred. Data is **not** a HA state attribute,
HA service/action, Recorder history reconstruction, invoice or charging schedule.

Built-in HA history/statistics cards query historical Recorder states/aggregates;
they do not represent the stored day-ahead quarter schedule or its future components.
The bundled dependency-free custom card uses the supported [custom-card interface](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/),
[native WebSocket API](https://developers.home-assistant.io/docs/api/websocket/)
and [async static-file registration](https://developers.home-assistant.io/blog/2024/06/18/async_register_static_paths/).
No HA/HACS/frontend monkeypatch, external JS/CDN or extra database is used.

## Troubleshooting

- **Custom element doesn't exist:** check the module URL/type in Resources, confirm
  beta.8 is installed, then reload/clear the app frontend cache. Do not add the
  integration repository as a HACS frontend repository.
- **Select an entity of a loaded site:** copy an actual PE sensor ID, load/repair
  that integration entry and verify the logged-in user can read the sensor.
- **Missing/Incomplete:** inspect the affected row, its date and missing component.
  Use native Configure to correct actual rates/periods, or await Nord Pool publication.
  Dashboard Refresh only reads stored data; **Check prices** in Configure performs
  normal verified retrieval. Tomorrow is never supplied from today's prices.
- **Optional ESTIMATED/UNVERIFIED entities:** new sites leave them disabled when
  provisional pricing is unconfigured; older entries are hidden by the integration,
  preserving IDs/history and user-owned hides. Explicit provisional configuration
  restores integration-hidden/disabled optional entities. They remain opt-in in the
  entity registry and never authorize CM.
- HACS uninstall retains price history; normal restart restores ledger records.
  The card is bundled under `custom_components/ha_energy_price_engine/www`, not
  copied to user `/config/www`. Remove its resource/dashboard card if PE is removed.

Cloud tests and screenshots use synthetic spot/private rates plus recorded Radius
responses. They do not establish owner contract correctness, live provider service
availability, Raspberry Pi capacity or physical charging behavior.
