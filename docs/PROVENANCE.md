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

Changes from the source are recorded in Git and ADR-001: independent storage
namespace/lifecycle, versioned consumer API, native site/rate configuration, durable
history/audit, stricter source verification and targeted options recalculation.
