# One bundled electricity-price card

No third-party card is needed. Under **Settings → Dashboards → three-dot menu →
Resources**, add this JavaScript module (enable Advanced mode on your HA profile if
Resources is hidden):

```yaml
url: /ha_energy_price_engine/energy-price-engine-card.js?v=0.1.0-beta.10
type: module
```

Reload the browser/app. Edit a dashboard, add a **Manual** card and paste:

```yaml
type: custom:energy-price-engine-card
```

One readable, loaded PE site is discovered automatically. With multiple sites the
card offers a named selector; no technical entity ID is required. To pin a card,
use `site_id: <id>` from the availability sensor's `site_id` attribute. This explicit
mapping is stable for that site, including renames; resets generate a new identity.
A complete panel-dashboard example is in [dashboard.yaml](dashboard.yaml). For a
YAML dashboard, put the same resource under `lovelace.resources` in configuration.yaml.

The card shows separate raw/final graphs for today and tomorrow, today's verified
DSO time bands, every local quarter, and a selected-quarter component/VAT/source
inspector. Select a bar or table interval. DST repeated hours show UTC offsets;
missing prices leave gaps. Values display øre/kWh with two decimals, while totals
use unrounded stored values. Horizontal tables scroll within the card on mobile.

**Full-day statistics** include all 92/96/100 calculated quarters immediately.
**Remaining-day statistics** cover a complete available suffix of today when
unverified earlier private rates prevent full-day coverage. The three native
statistic sensors change their friendly names accordingly and expose `scope`,
`used_slots`, `day_slots` and range attributes. A middle gap makes statistics
unavailable; PE does not skip that gap or pretend partial data is a complete day.
These are schedule statistics, not Recorder sample statistics or settled accounting.

Availability explains current/next/tomorrow readiness, missing components, the
source/verification failure, affected period and corrective action. Unknown current
price after first setup can be correct: the rate starts next complete quarter.
Tomorrow can be unpublished while today's future range is READY. After public rate
expiry, confirm new documented rates under Advanced. Missing rates are never zero.

The card is read-only and uses authenticated HA WebSocket commands filtered by
entity read permissions. It reads precomputed prices/cached source snapshots,
without provider requests, tariff recomposition or SQLite writes. Its two-day
schema is internal v2; Python consumer API v2 is documented separately.

## Native software screenshots

[Desktop dashboard](images/beta10/dashboard-desktop.png) ·
[Mobile dashboard](images/beta10/dashboard-mobile.png) ·
[Remaining-day/multiple sites](images/beta10/dashboard-remaining-mobile.png) ·
[DSO intervals](images/beta10/dashboard-grid-mobile.png) ·
[Component inspector](images/beta10/dashboard-inspector-mobile.png) ·
[Quarter table](images/beta10/dashboard-quarters-desktop.png) ·
[Nine-entity device](images/beta10/device-desktop.png) ·
[Danish saved setup](images/beta10/setup-saved-da-mobile.png).

These are actual disposable Home Assistant screens using recorded public tariffs and
fictional private rates, not owner installation screenshots. The
[simulation receipt](receipts/v0.1.0-beta.10-simulation.json) records hashes and results.
