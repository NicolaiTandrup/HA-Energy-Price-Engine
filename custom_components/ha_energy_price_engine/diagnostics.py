"""Redacted source, coverage and SQLite diagnostics without private contract labels."""

from .const import API_VERSION, DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    c = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if c is None:
        return {"api_version": API_VERSION, "loaded": False, "state": str(entry.state)}

    def storage_usage():
        import shutil

        path = c.price_engine.database.path
        return {
            "bytes": path.stat().st_size if path.exists() else 0,
            "free_bytes": shutil.disk_usage(path.parent).free if path.parent.exists() else None,
            "retention": "all_history",
            "memory_index": "all_history",
        }

    try:
        storage = await hass.async_add_executor_job(storage_usage)
    except OSError:
        storage = {"error": "Storage usage unavailable"}
    days = {}
    for day, report in c.schedule.days.get(c.site["id"], {}).items():
        days[day] = {
            key: report.get(key)
            for key in (
                "status",
                "expected_slots",
                "valid_slots",
                "last_success",
                "last_attempt",
                "missing_components",
                "failure_stage",
                "affected_period",
            )
        }
        grid = report.get("grid_source", {})
        days[day]["grid_source"] = {
            k: grid[k]
            for k in (
                "provider",
                "gln",
                "product",
                "charge_type",
                "unit",
                "vat_included",
                "version",
                "fetched_at",
            )
            if k in grid
        }
    return {
        "api_version": API_VERSION,
        "loaded": True,
        "version": c.integration_version,
        "area": c.site["area"],
        "timezone": c.site["timezone"],
        "dso_mode": c.site["dso_mode"],
        "days": days,
        "storage": storage,
        "ledger_records": len(c.price_engine.records.get(c.site["id"], ())),
        "revision": c.price_engine.revisions.get(c.site["id"], 0),
        "corrections": len(c.price_engine.audit.get(c.site["id"], [])),
        "load_error": bool(c.price_engine.load_errors),
    }
