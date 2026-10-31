"""Small saved-step native setup: official source, grid, markup, review."""

from copy import deepcopy
from uuid import uuid4

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .configuration import current_rate, settings, validate_site
from .const import COMPONENTS, DOMAIN
from .localization import flow_labels
from .money import decimal_amount
from .prices import async_source_defaults, ensure_official_nordpool


def select(values, key=None, multiple=False):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=list(values),
            **({"translation_key": key} if key else {}),
            multiple=multiple,
            mode="list" if multiple else "dropdown",
        )
    )


def amount_input():
    return selector.TextSelector(selector.TextSelectorConfig(suffix="øre/kWh"))


class Setup:
    """Both flows edit the same durable entry, without a second hidden Save."""

    async def _start(self, entry=None):
        self._entry = entry
        self._editing = False
        self._labels = await flow_labels(self.hass)
        if entry and entry.version != 4:
            return await self.async_step_reset()
        self.draft = (
            deepcopy(settings(entry))
            if entry
            else {
                "id": uuid4().hex,
                "name": "",
                "nordpool_entry": "",
                "area": "DK2",
                "timezone": "Europe/Copenhagen",
                "vat": 0.25,
                "dso_mode": "manual",
                "dated_components": [],
                "setup_step": "site",
            }
        )
        return await getattr(self, "async_step_" + self.draft.get("setup_step", "review"))()

    def _menu(self, step, choices, **placeholders):
        prefix = f"component.{DOMAIN}.config.step.{step}.menu_options."
        return self.async_show_menu(
            step_id=step,
            menu_options={key: self._labels[prefix + key] for key in choices},
            description_placeholders=placeholders,
        )

    def _form(self, step, schema, errors=None, **placeholders):
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema(schema),
            errors=errors or {},
            description_placeholders={"detail": "", **placeholders},
        )

    async def _save(self, site, next_step, *, follow_step=False):
        from . import apply_settings

        next_step = "review" if self._editing and not follow_step else next_step
        self.draft = validate_site({**site, "setup_step": next_step})
        loaded = await apply_settings(self.hass, self._entry, self.draft, reuse_sources=True)
        if not loaded:
            return self.async_abort(reason="saved_reload_failed")
        return await getattr(self, "async_step_" + next_step)()

    async def async_step_site(self, user_input=None):
        entries = [
            e for e in self.hass.config_entries.async_entries("nordpool") if e.disabled_by is None
        ]
        defaults = {
            **await async_source_defaults(self.hass),
            **{k: v for k, v in self.draft.items() if v},
        }
        errors = {}
        areas = {
            a
            for e in entries
            for a in e.options.get("areas", e.data.get("areas", []))
            if a in {"DK1", "DK2"}
        }
        if user_input is not None:
            try:
                await ensure_official_nordpool(self.hass)
                source = next(e for e in entries if e.entry_id == user_input["nordpool_entry"])
                supported = [
                    a
                    for a in source.options.get("areas", source.data.get("areas", []))
                    if a in {"DK1", "DK2"}
                ]
                area = supported[0] if len(supported) == 1 else user_input.get("area")
                if area not in supported or not user_input["name"].strip():
                    raise ValueError("Select the actual source area and a name")
                site = validate_site(
                    {**self.draft, **user_input, "area": area, "setup_step": "grid"}
                )
                if self._entry:
                    return await self._save(site, "grid")
                await self.async_set_unique_id(site["id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=site["name"], data=site)
            except ValueError, KeyError, StopIteration:
                errors["base"] = "invalid_source"
        if not entries:
            errors["base"] = "source_missing"
        value = {**defaults, **(user_input or {})}
        fields = {
            vol.Required("name", default=value.get("name", "")): str,
            vol.Required(
                "nordpool_entry",
                **({"default": value["nordpool_entry"]} if value.get("nordpool_entry") else {}),
            ): selector.ConfigEntrySelector(
                selector.ConfigEntrySelectorConfig(integration="nordpool")
            ),
        }
        if len(areas) > 1:
            fields[vol.Required("area", default=value.get("area", "DK2"))] = select(sorted(areas))
        return self._form("site", fields, errors)

    async def async_on_create_entry(self, result):
        self._entry = result["result"]
        self.draft = deepcopy(settings(self._entry))
        return await self.async_step_grid()

    async def async_step_grid(self, user_input=None):
        if user_input is not None:
            if user_input["grid"] == "radius_c":
                return await self._save({**self.draft, "dso_mode": "radius_c"}, "supplier")
            self.draft["dso_mode"] = "manual"
            # The completed grid choice is durable even before its rate is entered.
            return await self._save(self.draft, "grid_rate", follow_step=True)
        return self._form(
            "grid",
            {
                vol.Required("grid", default=self.draft["dso_mode"]): select(
                    ["radius_c", "manual"], "grid"
                )
            },
        )

    async def _rate(self, component, step, next_step, user_input):
        errors = {}
        old = next(
            (r for r in reversed(self.draft["dated_components"]) if r["id"] == component), None
        )
        if user_input is not None:
            try:
                rate = decimal_amount(user_input.get("amount"))
                site = current_rate(
                    self.draft,
                    component,
                    rate,
                    user_input["vat_included"],
                    dt_util.utcnow(),
                    whole_day=user_input.get("whole_day", False),
                )
                if component == "dso":
                    site["dso_mode"] = "manual"
                return await self._save(site, next_step)
            except ValueError, TypeError:
                errors["amount"] = "invalid_amount"
        value = user_input or (
            {"amount": str(old["amount"]), "vat_included": old["vat_included"]} if old else {}
        )
        return self._form(
            step,
            {
                vol.Required(
                    "amount",
                    **({"default": value["amount"]} if value.get("amount") is not None else {}),
                ): amount_input(),
                vol.Required("vat_included", default=value.get("vat_included", False)): bool,
                vol.Optional("whole_day", default=value.get("whole_day", False)): bool,
            },
            errors,
        )

    async def async_step_grid_rate(self, user_input=None):
        return await self._rate("dso", "grid_rate", "supplier", user_input)

    async def async_step_supplier(self, user_input=None):
        return await self._rate("supplier", "supplier", "review", user_input)

    async def async_step_review(self, user_input=None):
        self._editing = True
        self.draft = deepcopy(settings(self._entry))
        return self._menu(
            "review",
            ["done", "check", "site", "grid", "supplier", "advanced", "reset"],
            name=self.draft["name"],
        )

    async def async_step_done(self, user_input=None):
        if isinstance(self, config_entries.OptionsFlow):
            return self.async_create_entry(title="", data=dict(self._entry.options))
        return self.async_abort(reason="settings_saved")

    async def async_step_check(self, user_input=None):
        runtime = getattr(self._entry, "runtime_data", None)
        if runtime:
            await runtime.schedule.startup(force=True)
            await runtime.async_request_refresh()
        return await self.async_step_review()

    async def async_step_advanced(self, user_input=None):
        return self._menu("advanced", ["add_rate", "remove_rate", "review"])

    async def async_step_add_rate(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                if not user_input.get("confirm"):
                    raise ValueError("Confirm the complete effective period")
                rule = {k: v for k, v in user_input.items() if k != "confirm"}
                rule.update(
                    id=rule.pop("component"),
                    amount=decimal_amount(rule["amount"]),
                    unit="ore/kWh",
                    verified_on=str(dt_util.now().date()),
                )
                return await self._save(
                    {**self.draft, "dated_components": [*self.draft["dated_components"], rule]},
                    "review",
                )
            except ValueError, TypeError:
                errors["base"] = "invalid_rate"
        value = user_input or {}
        schema = {
            vol.Required("component", default=value.get("component", "supplier")): select(
                COMPONENTS, "component"
            ),
            vol.Required("amount", default=value.get("amount", "")): amount_input(),
            vol.Required("vat_included", default=value.get("vat_included", False)): bool,
            vol.Required("vat_rate", default=value.get("vat_rate", 0.25)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1, step="any", mode="box")
            ),
            vol.Required(
                "valid_from",
                **({"default": value["valid_from"]} if value.get("valid_from") else {}),
            ): selector.DateSelector(),
            vol.Required(
                "valid_to", **({"default": value["valid_to"]} if value.get("valid_to") else {})
            ): selector.DateSelector(),
            vol.Optional("hours", default=value.get("hours", [])): select(
                [str(h) for h in range(24)], multiple=True
            ),
            vol.Required("source", default=value.get("source", "User-confirmed rate")): str,
            vol.Required("confirm", default=False): bool,
        }
        return self._form("add_rate", schema, errors)

    async def async_step_remove_rate(self, user_input=None):
        rules = self.draft["dated_components"]
        if not rules:
            return await self.async_step_advanced()
        if user_input is not None:
            try:
                index = int(user_input["rate"])
                assert 0 <= index < len(rules)
                return await self._save(
                    {
                        **self.draft,
                        "dated_components": [r for i, r in enumerate(rules) if i != index],
                    },
                    "review",
                )
            except ValueError, AssertionError:
                pass
        return self._form(
            "remove_rate",
            {
                vol.Required("rate"): select(
                    [
                        {
                            "value": str(i),
                            "label": f"{r['id']} · {r['amount']} øre/kWh · {r['valid_from']} → {r['valid_to']}",
                        }
                        for i, r in enumerate(rules)
                    ]
                )
            },
        )

    async def async_step_reset(self, user_input=None):
        from .site_lifecycle import permanently_remove

        name = settings(self._entry).get("name", self._entry.title)
        errors = {}
        if user_input is not None:
            if user_input.get("confirm") and user_input.get("name") == name:
                try:
                    await permanently_remove(self.hass, self._entry)
                    return self.async_abort(reason="site_reset")
                except OSError, ValueError:
                    errors["base"] = "reset_failed"
            else:
                errors["base"] = "confirm_reset"
        return self._form(
            "reset",
            {vol.Required("name", default=""): str, vol.Required("confirm", default=False): bool},
            errors,
            name=name,
        )


class EnergyPriceConfigFlow(Setup, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 4

    async def async_step_user(self, user_input=None):
        return await self._start()

    async def async_step_reconfigure(self, user_input=None):
        return await self._start(self._get_reconfigure_entry())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergyPriceOptionsFlow()


class EnergyPriceOptionsFlow(Setup, config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        return await self._start(self.config_entry)
