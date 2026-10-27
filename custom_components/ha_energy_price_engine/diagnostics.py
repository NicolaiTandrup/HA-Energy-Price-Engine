"""Redacted operational diagnostics; no customer labels, identifiers or raw sources."""

import json
from datetime import timedelta

from homeassistant.util import dt as dt_util


async def async_get_config_entry_diagnostics(hass, entry):
    c = getattr(entry, "runtime_data", None)
    if c is None or entry.entry_id not in hass.data.get("ha_energy_price_engine", {}):
        return {"api_version": 1, "loaded": False, "state": str(entry.state)}
    now = dt_util.utcnow()
    rows = c.price_engine.lookup(c.site["id"], now, now + timedelta(microseconds=1))
    components = json.loads(rows[0].components_json).get("components", {}) if rows else {}
    source = json.loads(rows[0].source_json) if rows else {}
    # Whitelist public source metadata; omit the Nord Pool entry identifier and
    # free-form user source labels. These values explain verification provenance.
    public_source = {
        k: source[k]
        for k in ("kind", "area", "input_unit", "input_vat", "verified_at")
        if k in source
    }
    if "dso" in source:
        public_source["dso"] = {
            k: v
            for k, v in source["dso"].items()
            if k
            in {
                "provider",
                "gln",
                "product",
                "charge_type",
                "unit",
                "vat_included",
                "version",
                "effective_ranges",
                "fetched_at",
            }
        }

    def storage_usage():
        import shutil

        path = c.price_engine.database.path
        return {
            "bytes": path.stat().st_size if path.exists() else 0,
            "free_bytes": shutil.disk_usage(path.parent).free if path.parent.exists() else None,
            "retention": "preserve_all_referenced_history_no_automatic_pruning",
            "memory_index": "all_history",
        }

    try:
        storage = await hass.async_add_executor_job(storage_usage)
    except OSError:
        storage = {"error": "Storage usage unavailable"}
    from .component_status import component_snapshot

    snapshot = component_snapshot(hass, entry)
    public_components = {}
    for key, row in snapshot["components"].items():
        source = row["source"]
        if not source.startswith(
            ("https://www.ewii.dk/", "Rate specified by owner")
        ) and source not in {
            "Nord Pool",
            "Radius",
            "Energi Data Service",
            "calculated",
            "confirmed_vat",
        }:
            source = "user_confirmed_or_unavailable"
        public_components[key] = {**row, "source": source}
    return {
        "component_breakdown": public_components,
        "storage": storage,
        "api_version": 1,
        "raw_source_days": {
            day: {k: v for k, v in report.items() if k != "reason"}
            for day, report in c.price_updater.raw_reports.items()
        },
        "source_verification": public_source,
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
