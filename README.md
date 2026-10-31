# Home Assistant Energy Price Engine

Energy Price Engine (PE) calculates and stores verified 15-minute marginal
electricity prices. It combines official Nord Pool spot prices with grid tariffs,
Energinet charges, your supplier markup, electricity tax and VAT. Negative prices,
DK1/DK2, Europe/Copenhagen and 92/96/100-quarter days are supported.

**v0.1.0-beta.10 is a breaking development beta.** Recreate older beta sites after
backing up. API v2 replaces v1; unreleased EV Charge Manager requires an adapter
update. No production cutover, charging control or stable release is implied.

## Install and configure

1. Follow [HACS installation and reset](docs/HACS_DISTRIBUTION.md). Enable **Show beta
   versions**, explicitly select **v0.1.0-beta.10**, download and restart HA.
2. Add the **official Home Assistant Nord Pool integration** for DK1 or DK2. A legacy
   HACS Nordpool integration is not required and must not shadow the official domain.
3. Under **Settings → Devices & services → Add integration**, select **Energy Price
   Engine**. Name the site, select Nord Pool, confirm Radius C or enter your actual
   grid rate, and enter your supplier markup in **øre/kWh**. No private rate is guessed.
4. Accepted steps save immediately. Close and reopen **Configure** to resume.
   **Done — close setup** finishes. Add another PE entry for each independent site.
5. Register the bundled card resource and paste the [dashboard YAML](docs/PRICE_DASHBOARD.md).

## Nine sensors per site

Current raw spot, current final, next-quarter raw, next-quarter final, today's
average/minimum/maximum, current DSO tariff, and price availability. Ordinary prices
use **øre/kWh, two decimals**; calculations and the API keep full precision.
Availability attributes and the card expose the component breakdown, source,
coverage, revision, reason and corrective action without dozens of extra entities.

Daily statistics use the calculated schedule immediately, including past and future
quarters when all applicable rates are verified. A newly entered rate starts next
complete quarter unless you explicitly confirm it also applied earlier today.
Otherwise statistics say **Remaining-day** and show coverage; missing history is
never fabricated. [Pricing and statistics](docs/PRICE_DASHBOARD.md).

## Boundaries

PE owns price fetching, calculation, persistence and publishing. Consumers use the
[read-only Python API v2](docs/API.md); [CM migration handoff](docs/INTEROPERABILITY.md).
Reads do not fetch sources, recompose tariffs or touch SQLite. Full requested future
coverage and recent source verification are required for READY. Missing prices are
unavailable, never zero. Refresh times remain **13:05, 13:20, 13:40, 23:59 and 00:01**
Copenhagen time, with conditional retries when the requested day remains incomplete.

PE estimates variable charging costs from caller-supplied quarter-hour energy.
It does not reconstruct household bills, allocate subscriptions, infer heating
eligibility or control vehicles/chargers. Public national rates have explicit expiry
periods. The documented EWII household markup **0.030 DKK/kWh ex VAT applies only to
June–September 2026**; it is not a current/default/future or summer-house rate.

[Acceptance checklist](docs/BETA_ACCEPTANCE.md) · [Cleanup inventory](docs/MVP_CLEANUP.md)
· [Performance and recovery](docs/PERFORMANCE.md) · [Source attribution](docs/PROVENANCE.md)
· [Permanent development handoff](docs/DEVELOPMENT_STATUS.md). Cloud benchmarks do
not establish Raspberry Pi performance. MIT licensed, © Nicolai Tandrup.
