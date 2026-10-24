"""Redacted operational diagnostics; no customer labels, identifiers or raw sources."""

import json
from datetime import timedelta

from homeassistant.util import dt as dt_util


async def async_get_config_entry_diagnostics(hass, entry):
    c = entry.runtime_data
    now = dt_util.utcnow()
    rows = c.price_engine.lookup(c.site["id"], now, now + timedelta(microseconds=1))
    components = json.loads(rows[0].components_json).get("components", {}) if rows else {}
    return {
        "api_version": 1,
        "area": c.site["area"],
        "timezone": c.site["timezone"],
        "dso_mode": c.site.get("dso_mode", "manual"),
        "requested_days": {
            day: {k: v for k, v in report.items() if k != "reason"}
            for day, report in c.schedule.days.get(c.site["id"], {}).items()
        },
        "ledger_records": len(c.price_engine.records.get(c.site["id"], ())),
        "revision": c.price_engine.revisions.get(c.site["id"], 0),
        "corrections": len(c.price_engine.audit.get(c.site["id"], [])),
        "current_components": {
            key: {k: v for k, v in part.items() if k != "source"}
            for key, part in components.items()
        },
        "configured_periods": [
            {k: v for k, v in r.items() if k != "source"}
            for r in c.site.get("dated_components", [])
        ],
        "load_error": bool(c.price_engine.load_errors),
        "has_source_error": any(
            r.get("reason") for r in c.schedule.days.get(c.site["id"], {}).values()
        ),
    }
