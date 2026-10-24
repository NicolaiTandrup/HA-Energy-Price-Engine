# Home Assistant Energy Price Engine

A standalone native Home Assistant **developer preview** that owns electricity
price retrieval, tariff verification, calculation, durable 15-minute final prices
and publishing. EV Charge Manager, heating and batteries consume stored prices;
this integration contains no vehicle or charging controls.

Built from the tested pricing implementation in EV Charge Manager PRs
[#11](https://github.com/NicolaiTandrup/HA-EV-Charge-Manager/pull/11) and
[#12](https://github.com/NicolaiTandrup/HA-EV-Charge-Manager/pull/12).
[Source provenance](docs/PROVENANCE.md) · [Architecture](docs/ADR-001.md) ·
[API v1](docs/API.md) · [Development handoff](docs/DEVELOPMENT_STATUS.md)

## Preview installation and native configuration

Requires Home Assistant 2026.10+ and its official **Nord Pool** integration. For an
isolated development HA instance, copy `custom_components/ha_energy_price_engine`
to the HA configuration's `custom_components` directory and restart that instance.
HACS custom-repository metadata is included; catalog inclusion is not claimed.
There is no stable release and no authorization to deploy this preview to a live HA.

Add **Energy Price Engine** in Settings → Devices & services. Create one entry per
site with a stable ID, name, official Nord Pool entry, area (initially DK2), timezone
and explicit VAT fraction. Open its **Options** to configure:

- **Pricing / Supplier:** add or edit dated supplier markup and other components;
  select DKK/kWh or øre/kWh, VAT inclusion/fraction, source, verification and dates.
- **Tariffs:** verified automatic Radius C, manual dated DSO rules, or explicit
  manual fallback plus last verified cache. Manual locks take precedence.
- **Taxes / TSO:** explicit dated rates or the documented, bounded national baseline;
  verified heating/annual usage is optional and never invents future legislation.
- **Subscriptions:** use DKK/month; fixed charges never affect marginal slot ranking.

Dates are local, start inclusive/end exclusive. To schedule a new contract, end the
old period on the new start date and add the new period in the same options draft,
then **Save**. Equal-priority overlapping periods and invalid units/VAT are rejected.
Closing the editor without Save discards the draft. Configuration survives HA
restart; affected future stored prices are recalculated on change and audited.
Settled history stays intact. The options summary shows actual applied components,
source, periods, last check/change and current final price. Diagnostics expose
readiness/counts and redacted configuration; repair warnings point to missing data.
Unknown or expired rates leave pricing degraded, never silently zero.

**Documented EWII household example:** 0.030 DKK/kWh excluding VAT, from
2026-06-01 until 2026-10-01 (June–September invoices only). This is not an automatic
site default, a later contract or a summer-house rate. Enter separate verified
periods for each site. The public TSO baseline ends after 2026; tax 0.008 DKK/kWh
ex VAT ends after 2027. No later terms are inferred.

## Behavior and safety

Refreshes use Europe/Copenhagen: 13:05 primary, 13:20 and 13:40 conditional retries,
23:59 conditional rescue, 00:01 unconditional current-day source check, plus startup
catch-up. Complete UTC quarter-hour series (92/96/100 slots with DST) are validated
before atomic persistence. Verification-only checks do not reprice identical inputs.
Negative spot prices are supported. VAT is applied exactly once per component.

History is retained permanently with future correction audit and indexed read-only
range lookups. HA Store JSON snapshots grow with retained history; multi-year scale
needs measurement before production acceptance. Consumers must check readiness and
coverage; stale or missing prices are never free. No live Home Assistant, Node-RED
or charger changes, merges, stable releases or cutovers without owner approval.

## Development

Read AGENTS.md and docs/DEVELOPMENT_STATUS.md first. Use the existing isolated
checkout, Python 3.14.8 and the hash-verified dependency lock:

```sh
uv venv --python 3.14.8
uv pip sync --require-hashes requirements-dev.lock
.venv/bin/pytest --cov=custom_components.ha_energy_price_engine
.venv/bin/ruff check custom_components tests
.venv/bin/ruff format --check custom_components tests
docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest
```

Tests mock all service/network inputs. CI runs tests/Ruff, official hassfest and HACS
metadata validation. No integration service, credentials or hardware are needed to
develop/test. See the permanent handoff for actual local/remote results and remaining
acceptance gaps; presence of a workflow file is not a claim CI passed.
