# Implementation provenance

The pricing modules and their initial regressions were ported from
[NicolaiTandrup/HA-EV-Charge-Manager PR #11](https://github.com/NicolaiTandrup/HA-EV-Charge-Manager/pull/11)
and [PR #12](https://github.com/NicolaiTandrup/HA-EV-Charge-Manager/pull/12),
source head `9d949c6`, substantive pricing head
`6f972a554920ccd958ba4a77ccfa2147fd4c5b3f`.

Copyright (c) 2026 Nicolai Tandrup. MIT License, retained in root LICENSE.

Ported: price_engine.py, price_components.py, price_schedule.py, price_update.py,
prices.py, tariff_source.py, adapters.py; price-only types/validation from planner.py;
test_price_engine, test_price_components, test_price_schedule, test_tariff_source;
verified Radius Datahub fixture. No vehicle, optimizer, control or Node-RED code.
The original integration-dependent optimizer tests are replaced by producer
lifecycle/consumer contract tests here; price-only regressions are retained.

Changes from the source are recorded in Git and the cleanup inventory: independent storage
namespace/lifecycle, versioned consumer API, native site/rate configuration, durable
history/audit, stricter source verification and targeted options recalculation.

Beta.10 retains the proven dated calculation, source normalization, scheduler and
Radius adapter while removing obsolete invoice/provisional/entity-source branches.
The strict official normalization from adapters.py now lives in prices.py. SQLite
compression/recovery remains intact. Historical release receipts and tags preserve
earlier tested implementations; removal does not erase their attribution.

National 2026 charges: Energinet net 4.3 øre/kWh, system 7.2øre/kWh exVAT through
2026-12-31; electricity tax0.8 øre/kWh exVAT for 2026–2027. These bounded owner-verified
policy rates came from issue #8, verified2026-10-23; they are not a legislation scraper.
VAT 25% is applied once. Unknown later rates fail closed until explicitly verified.
The documented EWII household3 øre/kWh exVAT is June–September 2026 only. Beta.10
does not extrapolate it, use it as an onboarding default or scrape a different
public product as the owner's contract. Supplier amounts come from explicit input.
