"""Drive native wizard navigation while retaining beta.1 regression intent."""


async def options_review(hass, entry_id):
    result = await hass.config_entries.options.async_init(entry_id)
    if result["step_id"] != "wizard_review":
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"navigation": "review"}
        )
    return result


async def options_advanced(hass, entry_id):
    result = await options_review(hass, entry_id)
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "advanced"}
    )


async def save_options(hass, flow_id):
    await hass.config_entries.options.async_configure(flow_id, {"next_step_id": "wizard_review"})
    return await hass.config_entries.options.async_configure(
        flow_id, {"next_step_id": "wizard_save"}
    )


async def source_page(hass, name="Test site", source_type="nordpool"):
    result = await hass.config_entries.flow.async_init(
        "ha_energy_price_engine", context={"source": "user"}
    )
    if result["step_id"] == "wizard_resume":
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"draft": "new"})
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": name, "source_type": source_type}
    )
