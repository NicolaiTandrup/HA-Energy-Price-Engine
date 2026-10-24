"""Native verification repair: never dismiss degraded prices as fixed blindly."""

import voluptuous as vol
from homeassistant.components.repairs.models import RepairsFlow
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


class PricingRepairFlow(RepairsFlow):
    def __init__(self, entry_id):
        super().__init__()
        self.entry_id = entry_id

    async def async_step_init(self, user_input=None):
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        c = self.hass.data.get(DOMAIN, {}).get(self.entry_id)
        if c is None:
            return self.async_abort(reason="site_not_loaded")
        errors = {}
        if user_input is not None:
            try:
                await c.schedule.startup()
                await c.async_refresh()
                if c.data.get("status") == "READY":
                    return self.async_create_entry(data={})
            except HomeAssistantError, OSError:
                pass
            errors["base"] = "pricing_not_ready"
        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}), errors=errors)


async def async_create_fix_flow(hass, issue_id, data):
    return PricingRepairFlow((data or {}).get("entry_id", issue_id))
