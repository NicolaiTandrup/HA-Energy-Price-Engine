# Development handoff

Updated 2026-10-24. Read AGENTS.md first; this is the single permanent handoff.

## Active work

Branch: `feat/standalone-price-engine`, based on `981e489` (main).
Last pushed checkpoint: `e50d0df`.
Current checkpoint subject: `feat: port proven persistent pricing and tariff stack`.
Issues #1–#5 read in full from GitHub. Proven pricing core ported; integration/API/UI work pending.

## Evidence and decisions

- Main initially contains README and MIT license only; checkout clean.
- Studied EV Charge Manager PR #11 (`5c32dc9`) and #12
  (`9d949c6`; code checkpoint `6f972a554920ccd958ba4a77ccfa2147fd4c5b3f`).
- Reuse its price_engine, price_components, price_schedule, price_update, prices
  and tariff_source modules and regression tests. Separate price-only types from
  vehicle planning. New domain: `ha_energy_price_engine`; independent HA config
  entries represent sites. No EV/charging implementation belongs in this producer.
- Preserve UTC quarter hours, Copenhagen scheduling (13:05/13:20/13:40/23:59/00:01),
  atomic HA Store writes, settled history, no read-time I/O/arithmetic, VAT and source
  provenance. Extend with versioned immutable API, native configuration, diagnostics.
- EWII June–September 2026 household example only; future/other-site rates unknown.

## Validation and access

Read-only Git access works for both repositories. Local validation: Python 3.14.8, exact hash-verified upstream dependency lock;
`pytest tests/test_price_engine.py tests/test_price_components.py tests/test_price_schedule.py tests/test_tariff_source.py`: **36 passed**, zero skips. Ruff check and format pass.
No remote CI exists yet. GitHub API requests return proxy HTTP 403 (including gh); GitHub HTML
and Git work. Required API and optional Datahub domains added to environment draft;
saved configuration does not apply runtime networking or publish a snapshot.

## Next steps

1. Ported core and 36 regression cases complete; see docs/PROVENANCE.md.
2. Locked development environment is `.venv`; use `.venv/bin/python -m pytest`.
3. Add independent lifecycle, per-site native config/options UI, read-only API,
   diagnostics, schedule/source event integration, audit and permanent history.
4. Add mocked integration/contract/consumer-parity tests, Ruff and CI metadata checks.
5. Push milestones, open draft PR and inspect exact-head CI when API access permits.
   Record blockers honestly if proxy access remains unavailable.

No production systems touched; no merge, stable release or live controls authorized.
