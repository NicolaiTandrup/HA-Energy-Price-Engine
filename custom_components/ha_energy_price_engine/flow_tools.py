"""Shared native selectors and preserved selected-site management actions."""

import voluptuous as vol
from homeassistant.helpers import selector


def choice(items, translation_key=None):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[k for k, _ in items]
            if translation_key
            else [{"value": k, "label": v} for k, v in items],
            mode="list" if translation_key == "wizard_navigation" else "dropdown",
            **({"translation_key": translation_key} if translation_key else {}),
        )
    )


def number(minimum=0, maximum=None):
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum, **({"max": maximum} if maximum is not None else {}), step="any", mode="box"
        )
    )


class FlowTools:
    """Safe management actions reused by ordinary saved-step configuration."""

    _wizard_entry = None

    async def async_step_site_management(self, user_input=None):
        from .site_lifecycle import owned_files, permanently_remove

        entry = self._wizard_entry
        if entry is None:
            return self.async_abort(reason="site_not_loaded")
        errors = {}
        if user_input:
            if user_input.get("operation") == "archive":
                await self.hass.config_entries.async_remove(entry.entry_id)
                return self.async_abort(reason="site_archived")
            if not user_input.get("confirm") or user_input.get("site_id") != self.draft["id"]:
                errors["base"] = "deletion_confirmation"
            else:
                try:
                    await permanently_remove(self.hass, entry)
                    return self.async_abort(reason="site_deleted")
                except OSError, ValueError:
                    errors["base"] = "deletion_failed"
        try:
            paths = await self.hass.async_add_executor_job(owned_files, self.hass, entry)
            files = "\n".join(f"- .storage/{p.name}" for p in paths) or "—"
        except OSError, ValueError:
            files = "—"
        return self.async_show_form(
            step_id="site_management",
            errors=errors,
            description_placeholders={"site_id": self.draft["id"], "files": files},
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "operation", default=(user_input or {}).get("operation", "archive")
                    ): choice([("archive", "archive"), ("permanent", "permanent")], "site_removal"),
                    vol.Optional("site_id", default=(user_input or {}).get("site_id", "")): str,
                    vol.Required("confirm", default=(user_input or {}).get("confirm", False)): bool,
                }
            ),
        )

    async def async_step_hacs_channel(self, user_input=None):
        errors = {}
        if user_input and user_input.get("confirm"):
            from .hacs_channel import enable_beta_channel

            try:
                latest = await enable_beta_channel(self.hass)
                return self.async_abort(
                    reason="hacs_channel_updated", description_placeholders={"version": latest}
                )
            except ValueError:
                errors["base"] = "hacs_channel_failed"
        return self.async_show_form(
            step_id="hacs_channel",
            errors=errors,
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
        )
