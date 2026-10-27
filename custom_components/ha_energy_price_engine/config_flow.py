"""Native site and dated pricing editor; ordinary use needs no Python or YAML."""

import json
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .configuration import settings, validate_site
from .const import COMPONENTS, DOMAIN
from .sources import BASES, UNIT_MULTIPLIERS, async_source_defaults, ensure_official_nordpool
from .status import slot_breakdown, source_status


def select(options):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=list(options), mode="dropdown", translation_key="values"
        )
    )


def site_schema(value=None, *, initial=False):
    value = value or {}
    fields = {}
    if initial:
        fields[vol.Required("id")] = str
    fields.update(
        {
            vol.Required("name", default=value.get("name", "")): str,
            vol.Required("source_type", default=value.get("source_type", "nordpool")): select(
                [
                    {"value": "nordpool", "label": "Official Home Assistant Nord Pool"},
                    {"value": "entity", "label": "Verified provider entity"},
                ]
            ),
            vol.Optional(
                "price_entity",
                **({"default": value["price_entity"]} if value.get("price_entity") else {}),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required("price_unit", default=value.get("price_unit", "DKK/MWh")): select(
                UNIT_MULTIPLIERS
            ),
            vol.Required("price_basis", default=value.get("price_basis", "spot_ex_vat")): select(
                BASES
            ),
            vol.Required("price_attribute", default=value.get("price_attribute", "slots")): str,
            vol.Required("stale_minutes", default=value.get("stale_minutes", 40)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=2880)
            ),
            vol.Optional(
                "nordpool_entry",
                **({"default": value["nordpool_entry"]} if value.get("nordpool_entry") else {}),
            ): selector.ConfigEntrySelector(
                selector.ConfigEntrySelectorConfig(integration="nordpool")
            ),
            vol.Required("area", default=value.get("area", "DK2")): str,
            vol.Required("timezone", default=value.get("timezone", "Europe/Copenhagen")): str,
            vol.Required("vat", default=value.get("vat", 0.25)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1, step=0.01, mode="box")
            ),
        }
    )
    return vol.Schema(fields)


def rule_schema(value=None):
    value = value or {}
    return vol.Schema(
        {
            vol.Required("id", default=value.get("id", "supplier")): select(
                [{"value": key, "label": key.replace("_", " ").capitalize()} for key in COMPONENTS]
            ),
            vol.Required("amount", default=value.get("amount", 0)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, step="any", mode="box")
            ),
            vol.Required("unit", default=value.get("unit", "DKK/kWh")): select(
                ("DKK/kWh", "ore/kWh", "DKK/month")
            ),
            vol.Required("vat_included", default=value.get("vat_included", False)): bool,
            vol.Required("vat_rate", default=value.get("vat_rate", 0.25)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1, step=0.01, mode="box")
            ),
            vol.Required(
                "valid_from", **({"default": value["valid_from"]} if "valid_from" in value else {})
            ): selector.DateSelector(),
            vol.Required(
                "valid_to", **({"default": value["valid_to"]} if "valid_to" in value else {})
            ): selector.DateSelector(),
            vol.Required("source", default=value.get("source", "")): str,
            vol.Required(
                "verified_on",
                **({"default": value["verified_on"]} if "verified_on" in value else {}),
            ): selector.DateSelector(),
            vol.Optional(
                "hours", default=[str(h) for h in value.get("hours", [])]
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    multiple=True,
                    options=[
                        {"value": str(h), "label": f"{h:02d}:00–{h + 1:02d}:00"} for h in range(24)
                    ],
                )
            ),
            vol.Required("locked", default=value.get("locked", True)): bool,
            vol.Required("eligibility", default=value.get("eligibility", "all")): select(
                ("all", "heating_above_4000")
            ),
        }
    )


class LegacyEnergyPriceConfigFlow(config_entries.ConfigFlow):
    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergyPriceOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                site = validate_site({**user_input, "dated_components": [], "dso_mode": "manual"})
                source = self.hass.config_entries.async_get_entry(site["nordpool_entry"])
                if site["source_type"] == "nordpool" and (
                    source is None or source.domain != "nordpool"
                ):
                    raise ValueError("Select an official Nord Pool config entry")
                if site["source_type"] == "nordpool":
                    await ensure_official_nordpool(self.hass)
                await self.async_set_unique_id(site["id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=site["name"], data=site)
            except ValueError, KeyError, TypeError, ZoneInfoNotFoundError:
                errors["base"] = "invalid_configuration"
        return self.async_show_form(
            step_id="user",
            data_schema=site_schema(
                {**await async_source_defaults(self.hass), **(user_input or {})}, initial=True
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            try:
                site = validate_site(
                    {**settings(entry), **user_input, "id": entry.unique_id or entry.data["id"]}
                )
                source = self.hass.config_entries.async_get_entry(site["nordpool_entry"])
                if site["source_type"] == "nordpool" and (
                    source is None or source.domain != "nordpool"
                ):
                    raise ValueError("Official Nord Pool entry required")
                if site["source_type"] == "nordpool":
                    await ensure_official_nordpool(self.hass)
                if entry.update_listeners:
                    return self.async_update_and_abort(entry, options=site, title=site["name"])
                return self.async_update_reload_and_abort(entry, options=site, title=site["name"])
            except ValueError, TypeError, KeyError, ZoneInfoNotFoundError:
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=site_schema(user_input),
                    errors={"base": "invalid_configuration"},
                )
        return self.async_show_form(step_id="reconfigure", data_schema=site_schema(settings(entry)))


class LegacyEnergyPriceOptionsFlow(config_entries.OptionsFlow):
    def __init__(self):
        self.draft = None
        self.index = None
        self.backup_result = None

    async def async_step_init(self, user_input=None):
        if self.draft is None:
            self.draft = deepcopy(settings(self.config_entry))
        return self.async_show_menu(
            step_id="init",
            description_placeholders={"pricing_summary": self._summary()},
            menu_options=[
                "site",
                "supplier",
                "add_rate",
                "edit_rate",
                "remove_rate",
                "dso",
                "taxes",
                "storage",
                "breakdown",
                "save",
            ],
        )

    def _summary(self):
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return "No runtime data. Add all required dated components, then Save and check diagnostics."
        now = dt_util.utcnow()
        rows = runtime.price_engine.lookup(runtime.site["id"], now, now + timedelta(microseconds=1))
        report = runtime.data or {}
        status = source_status(runtime, now)
        lines = [
            f"Site: {self.draft['name']}; source: {status['source']}; area: {status['area']}; "
            "currency: DKK; resolution: 15 minutes",
            f"Status: {status['health']}; last check: {report.get('last_attempt', 'never')}; "
            f"last verified: {status['last_success'] or 'never'}; next update: {status['next_scheduled_update']}",
        ]
        if rows:
            row = rows[0]
            lines.append(
                f"Current final price: {row.final_price_incl_vat:.6f} DKK/kWh incl VAT; "
                f"last changed: {row.calculated_at.isoformat()}; revision {row.revision}"
            )
            provenance = json.loads(row.source_json)
            for name, part in json.loads(row.components_json).get("components", {}).items():
                lines.append(
                    f"{name}: {part['incl_vat']:.6f} DKK/kWh incl VAT; "
                    f"source: {part.get('source', provenance.get('dso', {}).get('provider', 'official Nord Pool'))}; "
                    f"period: {part.get('valid_from', 'see diagnostics')} – {part.get('valid_to', 'see diagnostics')}; "
                    f"manual lock: {part.get('locked', False)}"
                )
        else:
            lines.append(
                "No verified current slot. Configure missing rates; consult diagnostics for requested dates."
            )
        if self.backup_result:
            lines.append(self.backup_result)
        return "\n".join(lines)

    async def async_step_site(self, user_input=None):
        if user_input is not None:
            return await self._stage("site", user_input, site_schema(user_input))
        return self.async_show_form(step_id="site", data_schema=site_schema(self.draft))

    async def async_step_supplier(self, user_input=None):
        schema = vol.Schema(
            {
                vol.Required("supplier", default=self.draft.get("supplier", "custom")): select(
                    ("custom", "ewii")
                )
            }
        )
        if user_input is not None:
            return await self._stage("supplier", user_input, schema)
        return self.async_show_form(step_id="supplier", data_schema=schema)

    async def async_step_reconfigure_source(self, user_input=None):
        return await self.async_step_site(user_input)

    async def async_step_dso(self, user_input=None):
        schema = vol.Schema(
            {
                vol.Required(
                    "dso_tariff_class", default=self.draft.get("dso_tariff_class", "C")
                ): str,
                vol.Required("dso_mode", default=self.draft.get("dso_mode", "manual")): select(
                    ("manual", "radius_c")
                ),
                vol.Required(
                    "dso_manual_fallback", default=self.draft.get("dso_manual_fallback", False)
                ): bool,
                vol.Required(
                    "dso_stale_days", default=self.draft.get("dso_stale_days", 7)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }
        )
        if user_input is not None:
            return await self._stage("dso", user_input, schema)
        return self.async_show_form(step_id="dso", data_schema=schema)

    async def async_step_taxes(self, user_input=None):
        schema = vol.Schema(
            {
                vol.Required(
                    "danish_public_rates", default=self.draft.get("danish_public_rates", False)
                ): bool,
                vol.Required(
                    "heating_registered", default=self.draft.get("heating_registered", False)
                ): bool,
                vol.Required(
                    "annual_usage_kwh", default=self.draft.get("annual_usage_kwh", 0)
                ): vol.All(vol.Coerce(float), vol.Range(min=0)),
                vol.Optional(
                    "usage_year",
                    **(
                        {"default": self.draft["usage_year"]}
                        if self.draft.get("usage_year")
                        else {}
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=2000, max=2100)),
            }
        )
        if user_input is not None:
            return await self._stage("taxes", user_input, schema)
        return self.async_show_form(step_id="taxes", data_schema=schema)

    async def _stage(self, step, changes, schema):
        try:
            proposed = validate_site({**self.draft, **changes})
            source = self.hass.config_entries.async_get_entry(proposed["nordpool_entry"])
            if (
                step == "site"
                and proposed["source_type"] == "nordpool"
                and (source is None or source.domain != "nordpool")
            ):
                raise ValueError("Official Nord Pool entry required")
            if step == "site" and proposed["source_type"] == "nordpool":
                await ensure_official_nordpool(self.hass)
            self.draft = proposed
            return await self.async_step_init()
        except ValueError, TypeError, KeyError, ZoneInfoNotFoundError:
            return self.async_show_form(
                step_id=step, data_schema=schema, errors={"base": "invalid_configuration"}
            )

    async def async_step_add_rate(self, user_input=None):
        if user_input is not None:
            return await self._rate("add_rate", user_input, None)
        return self.async_show_form(step_id="add_rate", data_schema=rule_schema())

    async def _choose(self, step, user_input):
        rules = self.draft.get("dated_components", [])
        if not rules:
            return await self.async_step_advanced()
        options = [
            {
                "value": str(i),
                "label": f"{r['id']}: {r['amount']} {r['unit']} ({r['valid_from']} – {r['valid_to']})",
            }
            for i, r in enumerate(rules)
        ]
        return self.async_show_form(
            step_id=step, data_schema=vol.Schema({vol.Required("rate"): select(options)})
        )

    async def async_step_edit_rate(self, user_input=None):
        if user_input is not None:
            self.index = int(user_input["rate"])
            return await self.async_step_rate()
        return await self._choose("edit_rate", user_input)

    async def async_step_rate(self, user_input=None):
        if user_input is not None:
            return await self._rate("rate", user_input, self.index)
        return self.async_show_form(
            step_id="rate", data_schema=rule_schema(self.draft["dated_components"][self.index])
        )

    async def _rate(self, step, rule, index):
        rules = deepcopy(self.draft.get("dated_components", []))
        if index is None:
            rules.append(rule)
        else:
            rules[index] = rule
        return await self._stage(step, {"dated_components": rules}, rule_schema(rule))

    async def async_step_remove_rate(self, user_input=None):
        if user_input is not None:
            rules = deepcopy(self.draft["dated_components"])
            rules.pop(int(user_input["rate"]))
            self.draft["dated_components"] = rules
            return await self.async_step_init()
        return await self._choose("remove_rate", user_input)

    async def async_step_breakdown(self, user_input=None):
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return self.async_abort(reason="site_not_loaded")
        now = dt_util.utcnow()
        zone = ZoneInfo(runtime.site["timezone"])
        from .price_engine import day_bounds

        day = now.astimezone(zone).date()
        start, _ = day_bounds(day, runtime.site["timezone"])
        _, end = day_bounds(day + timedelta(days=1), runtime.site["timezone"])
        rows = runtime.price_engine.lookup(runtime.site["id"], start, end)
        explanation = "Select a stored quarter to inspect its original amounts and verification. No source is fetched."
        if user_input:
            try:
                selected = datetime.fromisoformat(user_input["slot"])
                if selected not in {row.start for row in rows}:
                    raise ValueError("Slot not in displayed range")
                explanation = slot_breakdown(runtime, selected, now)
            except ValueError, KeyError, TypeError:
                explanation = (
                    "Select an available quarter from the list. Missing prices are not zero."
                )
        if not rows:
            explanation = "No stored quarters for today/tomorrow. Configure required components and check source readiness."
        return self.async_show_form(
            step_id="breakdown",
            data_schema=vol.Schema(
                {
                    vol.Optional("slot"): select(
                        [
                            {
                                "value": r.start.isoformat(),
                                "label": f"{r.start.astimezone(zone).isoformat()} — {r.final_price_incl_vat:.6f} DKK/kWh",
                            }
                            for r in rows
                        ]
                    )
                }
            ),
            description_placeholders={"slot_breakdown": explanation},
        )

    async def async_step_storage(self, user_input=None):
        result = "No backup created in this editor session."
        errors = {}
        if user_input is not None:
            runtime = getattr(self.config_entry, "runtime_data", None)
            if runtime is None:
                errors["base"] = "site_not_loaded"
            else:
                from uuid import uuid4

                database = runtime.price_engine.database
                destination = database.path.with_name(database.path.name + ".backup-" + uuid4().hex)
                try:
                    await database.async_backup(destination)
                    self.backup_result = f"✓ .storage/{destination.name}"
                    return await self.async_step_init()
                except OSError:
                    errors["base"] = "backup_failed"
        return self.async_show_form(
            step_id="storage",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"backup_result": result},
        )

    async def async_step_save(self, user_input=None):
        # ConfigEntry options are HA-managed durable storage; the update listener
        # audits the old/new configuration and reprices affected future rows.
        return self.async_create_entry(title="", data=validate_site(self.draft))


from .wizard import Wizard  # noqa: E402


class EnergyPriceConfigFlow(Wizard, LegacyEnergyPriceConfigFlow, domain=DOMAIN):
    VERSION = 3

    async def async_step_user(self, user_input=None):
        return await self._start_wizard()

    async def async_step_reconfigure(self, user_input=None):
        return await self._start_wizard(self._get_reconfigure_entry())

    _rate = LegacyEnergyPriceOptionsFlow._rate
    _stage = LegacyEnergyPriceOptionsFlow._stage
    _choose = LegacyEnergyPriceOptionsFlow._choose
    async_step_add_rate = LegacyEnergyPriceOptionsFlow.async_step_add_rate
    async_step_edit_rate = LegacyEnergyPriceOptionsFlow.async_step_edit_rate
    async_step_rate = LegacyEnergyPriceOptionsFlow.async_step_rate
    async_step_remove_rate = LegacyEnergyPriceOptionsFlow.async_step_remove_rate

    async def async_step_init(self, user_input=None):
        await self._persist("advanced")
        return await self.async_step_advanced()

    async def async_step_advanced(self, user_input=None):
        return self.async_show_menu(
            step_id="advanced",
            description_placeholders={
                "draft_status": self._state()
                + ("\n" + self.backup_result if getattr(self, "backup_result", None) else "")
            },
            menu_options=[
                "wizard_review",
                "wizard_grid",
                "wizard_supplier",
                "wizard_charges",
                "add_rate",
                "edit_rate",
                "remove_rate",
            ],
        )


class EnergyPriceOptionsFlow(Wizard, LegacyEnergyPriceOptionsFlow):
    async def async_step_init(self, user_input=None):
        if self.draft is None:
            return await self._start_wizard(self.config_entry)
        await self._persist("advanced")
        return await self.async_step_advanced()

    async def async_step_advanced(self, user_input=None):
        self._advanced = True
        return self.async_show_menu(
            step_id="advanced",
            description_placeholders={
                "draft_status": self._state()
                + ("\n" + self.backup_result if getattr(self, "backup_result", None) else "")
            },
            menu_options=[
                "wizard_review",
                "wizard_grid",
                "wizard_supplier",
                "wizard_charges",
                "add_rate",
                "edit_rate",
                "remove_rate",
                "storage",
                "breakdown",
            ],
        )
