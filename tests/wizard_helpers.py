"""Drive current native setup; ordinary pages already persist accepted settings."""


async def options_review(hass, entry_id):
    return await hass.config_entries.options.async_init(entry_id)


async def options_advanced(hass, entry_id):
    result = await options_review(hass, entry_id)
    for step in ("setup_final", "advanced"):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": step}
        )
    return result


async def options_rates(hass, entry_id):
    result = await options_advanced(hass, entry_id)
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "rates"}
    )


async def save_options(hass, flow_id):
    # Review does not commit a hidden draft.
    return await hass.config_entries.options.async_configure(
        flow_id, {"next_step_id": "setup_review"}
    )


async def source_page(hass, name="Test site", source_type="nordpool"):
    result = await hass.config_entries.flow.async_init(
        "ha_energy_price_engine", context={"source": "user"}
    )
    entries = hass.config_entries.async_entries("nordpool")
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": name, "nordpool_entry": entries[0].entry_id if entries else ""}
    )
