"""Source, grid and markup: accepted pages update the actual site immediately."""

from copy import deepcopy
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import voluptuous as vol
from homeassistant.helpers import selector
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .configuration import settings, validate_site
from .const import DOMAIN
from .contracts import current_contract
from .flow_tools import FlowTools, choice, money_input, number
from .money import decimal_amount
from .sources import async_source_defaults, ensure_official_nordpool


class SimpleSetup(FlowTools):
    """Current settings, not a hidden draft. Advanced rules remain explicit."""

    async def _start_setup(self, entry=None):
        from .localization import flow_labels

        self._flow_labels = await flow_labels(self.hass)
        self._wizard_entry = entry
        self._initial = entry is None
        self._editing = False
        self._forms, self._added, self._pending = {}, {}, []
        self._initial_drafts = {}
        self.draft = (
            deepcopy(settings(entry))
            if entry
            else {
                **await async_source_defaults(self.hass),
                "source_type": "nordpool",
                "dated_components": [],
                "dso_mode": "manual",
                "vat": 0.25,
                "supplier": "custom",
                "display_unit": "øre/kWh",
            }
        )
        if entry is None:
            return await self.async_step_setup_site()
        self._progress_store = Store(self.hass, 1, f"{DOMAIN}.{entry.entry_id}.setup")
        progress = await self._progress_store.async_load() or {}
        self._saved_step = progress.get("saved", "")
        target = progress.get("next", "setup_review")
        if target == "setup_tax":
            # Public national defaults need no redundant confirmation. Existing
            # accepted heating evidence/rules remain unchanged and editable.
            target = "setup_review"
        if target not in {
            "setup_site",
            "setup_area",
            "setup_grid",
            "setup_supplier",
            "setup_contract",
            "setup_tax",
            "setup_heating",
            "setup_review",
        }:
            target = "setup_review"
        return await getattr(self, "async_step_" + target)()

    async def _save_step(self, site, next_step, saved):
        from . import apply_settings

        previous = self.draft
        current = deepcopy(settings(self._wizard_entry))
        for key, value in site.items():
            if key not in previous or value != previous[key]:
                current[key] = deepcopy(value)
        for key in previous.keys() - site.keys():
            current.pop(key, None)
        if site.get("dated_components") != previous.get("dated_components"):
            before = previous.get("dated_components", [])
            after = site.get("dated_components", [])
            changed_ids = {
                r["id"]
                for r in before + after
                if [x for x in before if x["id"] == r["id"]]
                != [x for x in after if x["id"] == r["id"]]
            }
            current["dated_components"] = [
                r
                for r in settings(self._wizard_entry).get("dated_components", [])
                if r["id"] not in changed_ids
            ] + [r for r in after if r["id"] in changed_ids]
        self.draft = validate_site(current)
        if self._editing and next_step in {"setup_grid", "setup_supplier", "setup_tax"}:
            next_step = "setup_review"
        self._loaded = await apply_settings(
            self.hass, self._wizard_entry, self.draft, reuse_sources=True
        )
        self._saved_step = saved
        await self._progress_store.async_save({"next": next_step, "saved": saved})
        return await getattr(self, "async_step_" + next_step)()

    async def _simple_form(self, step, fields, progress, data=None, errors=None, **placeholders):
        from .localization import review_labels

        labels = await review_labels(self.hass)
        raw = data or {}
        schema = {}
        for key, validator in fields.items():
            default = raw.get(key.schema, key.default)
            schema[type(key)(key.schema, default=default)] = validator
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema(schema),
            errors=errors or {},
            description_placeholders={
                "progress": progress,
                "saved": labels.get("saved_" + getattr(self, "_saved_step", ""), ""),
                **placeholders,
            },
        )

    async def async_step_setup_site(self, user_input=None):
        site = deepcopy(self.draft)
        errors = {}
        entity = site.get("source_type") == "entity" and self._wizard_entry is not None
        if user_input is not None:
            try:
                name = user_input.get("name", "").strip()
                if not name:
                    errors["name"] = "name_required"
                    raise ValueError("name")
                site["name"] = name
                if not self._wizard_entry:
                    used = {e.unique_id for e in self.hass.config_entries.async_entries(DOMAIN)}
                    base = slugify(name)[:55] or "site"
                    key = base
                    while key in used:
                        key = base + "_" + uuid4().hex[:7]
                    site["id"] = key
                if not entity:
                    entry = self.hass.config_entries.async_get_entry(user_input["nordpool_entry"])
                    if not entry or entry.domain != "nordpool":
                        errors["nordpool_entry"] = "source_required"
                        raise ValueError("source")
                    try:
                        await ensure_official_nordpool(self.hass)
                    except ValueError:
                        errors["nordpool_entry"] = "official_required"
                        raise
                    areas = entry.options.get("areas", entry.data.get("areas", []))
                    if not isinstance(areas, list) or not areas:
                        errors["nordpool_entry"] = "source_area_required"
                        raise ValueError("area")
                    site.update(
                        nordpool_entry=entry.entry_id,
                        source_type="nordpool",
                        price_unit="DKK/MWh",
                        price_basis="spot_ex_vat",
                    )
                    selected_area = user_input.get(
                        "area", areas[0] if len(areas) == 1 else site.get("area")
                    )
                    if selected_area not in areas:
                        errors["area"] = "unsupported_area"
                        raise ValueError("area")
                    site["area"] = selected_area
                    if site["area"] not in {"DK1", "DK2"}:
                        errors["area"] = "unsupported_area"
                        raise ValueError("unsupported_country")
                    site.setdefault("timezone", "Europe/Copenhagen")
                    if not self._wizard_entry:
                        site["danish_public_rates"] = True
                return await self._create_or_save_site(site)
            except (ValueError, KeyError, TypeError) as err:
                self._error_detail = str(err)
                if not errors:
                    errors["base"] = "invalid_configuration"
        fields = {vol.Required("name", default=site.get("name", "")): str}
        if not entity:
            fields[
                vol.Required(
                    "nordpool_entry",
                    **({"default": site["nordpool_entry"]} if site.get("nordpool_entry") else {}),
                )
            ] = selector.ConfigEntrySelector(
                selector.ConfigEntrySelectorConfig(integration="nordpool")
            )
        if not entity:
            available = {
                a
                for e in self.hass.config_entries.async_entries("nordpool")
                for a in e.options.get("areas", e.data.get("areas", []))
                if a in {"DK1", "DK2"}
            }
            if len(available) > 1:
                fields[
                    vol.Required(
                        "area",
                        **({"default": site["area"]} if site.get("area") in available else {}),
                    )
                ] = choice([(a, a) for a in sorted(available)])
        return await self._simple_form("setup_site", fields, "1 / 3", user_input, errors)

    async def async_step_setup_area(self, user_input=None):
        source = self.hass.config_entries.async_get_entry(self.draft.get("nordpool_entry", ""))
        areas = source.options.get("areas", source.data.get("areas", [])) if source else []
        if user_input and user_input.get("area") in {"DK1", "DK2"} & set(areas):
            self.draft.update(area=user_input["area"], timezone="Europe/Copenhagen")
            if not self._wizard_entry:
                self.draft["danish_public_rates"] = True
            return await self._create_or_save_site(self.draft)
        return await self._simple_form(
            "setup_area",
            {vol.Required("area"): choice([(k, k) for k in areas if k in {"DK1", "DK2"}])},
            "1 / 3",
            user_input,
            {"area": "unsupported_area"} if user_input else {},
        )

    async def _create_or_save_site(self, site):
        await self.hass.async_add_executor_job(ZoneInfo, site["timezone"])
        site = validate_site(site)
        if self._wizard_entry:
            return await self._save_step(site, "setup_grid", "site")
        self.draft = site
        await self.async_set_unique_id(site["id"])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=site["name"], data=site)

    async def async_on_create_entry(self, result):
        self._wizard_entry = result["result"]
        self._initial = False
        self._progress_store = Store(self.hass, 1, f"{DOMAIN}.{self._wizard_entry.entry_id}.setup")
        self._saved_step = "site"
        await self._progress_store.async_save({"next": "setup_grid", "saved": "site"})
        # HA explicitly supports a FORM returned after entry creation. The entry
        # is already persisted/set up; subsequent pages operate on that same ID.
        return await self.async_step_setup_grid()

    async def async_step_setup_grid(self, user_input=None):
        if self.draft.get("price_basis") == "all_in":
            return await self._save_step(self.draft, "setup_supplier", "grid")
        errors = {}
        if user_input:
            mode = user_input.get("grid")
            if mode == "manual":
                return await self.async_step_setup_grid_rate()
            if mode == "radius_c":
                site = {**self.draft, "dso_mode": "radius_c", "dso_tariff_class": "C"}
                return await self._save_step(site, "setup_supplier", "grid")
            if mode == "keep":
                return await self._save_step(self.draft, "setup_supplier", "grid")
            errors["grid"] = "grid_required"
        options = [("radius_c", "radius_c"), ("manual", "manual")]
        if self._wizard_entry and any(
            r["id"] == "dso" for r in self.draft.get("dated_components", [])
        ):
            options.insert(0, ("keep", "keep"))
        return await self._simple_form(
            "setup_grid",
            {
                vol.Required(
                    "grid",
                    default="radius_c"
                    if self.draft.get("dso_mode") == "radius_c"
                    else "keep"
                    if options[0][0] == "keep"
                    else vol.UNDEFINED,
                ): choice(options, "simple_grid")
            },
            "2 / 3",
            user_input,
            errors,
        )

    async def async_step_setup_grid_rate(self, user_input=None):
        errors = {}
        if user_input:
            if not user_input.get("confirm"):
                errors["confirm"] = "confirmation_required"
            else:
                now = dt_util.utcnow()
                day = str(now.astimezone(ZoneInfo(self.draft["timezone"])).date())
                new_rule = {
                    "id": "dso",
                    "amount": user_input["amount"],
                    "unit": "ore/kWh",
                    "vat_included": user_input["vat_included"],
                    "vat_rate": self.draft["vat"],
                    "valid_from": day,
                    "valid_to": "9999-12-31",
                    "source": "user_confirmed_current_grid_rate",
                    "verified_on": day,
                    "locked": True,
                }
                from .contracts import replace_current_rules

                retained, segments = replace_current_rules(
                    self.draft.get("dated_components", []), new_rule, day
                )
                rules = retained + segments
                try:
                    from datetime import UTC, datetime
                    from math import ceil

                    site = {
                        **self.draft,
                        "dated_components": rules,
                        "dso_mode": "manual",
                        "pricing_start": datetime.fromtimestamp(
                            ceil(now.timestamp() / 900) * 900, UTC
                        ).isoformat(),
                    }
                    return await self._save_step(site, "setup_supplier", "grid")
                except ValueError:
                    errors["base"] = "invalid_rate"
        return await self._simple_form(
            "setup_grid_rate",
            {
                vol.Required("amount"): number(),
                vol.Required("vat_included", default=True): bool,
                vol.Required("confirm", default=False): bool,
            },
            "2 / 3",
            user_input,
            errors,
        )

    async def async_step_setup_supplier(self, user_input=None):
        """Ordinary charging setup asks for a markup, not an invoice/product model."""
        if self.draft.get("price_basis") == "all_in":
            return await self._save_step(self.draft, "setup_review", "supplier")
        errors = {}
        if user_input is not None:
            raw = user_input.get("amount", "").strip()
            if raw:
                try:
                    amount = decimal_amount(raw)
                    site = current_contract(
                        self.draft,
                        amount,
                        user_input["vat_included"],
                        None,
                        False,
                        dt_util.utcnow(),
                        source="user_confirmed_current_supplier",
                    )
                    # An ordinary markup edit preserves optional accounting data.
                    site["dated_components"] = [
                        r for r in site["dated_components"] if r["id"] != "supplier_subscription"
                    ] + [
                        r
                        for r in self.draft.get("dated_components", [])
                        if r["id"] == "supplier_subscription"
                    ]
                    return await self._save_step(site, "setup_review", "supplier")
                except (ValueError, KeyError, TypeError) as err:
                    self._error_detail = str(err)
                    errors["amount"] = "invalid_decimal"
            else:
                return await self._save_step(self.draft, "setup_review", "supplier")
        today = str(dt_util.utcnow().astimezone(ZoneInfo(self.draft["timezone"])).date())
        existing = [
            r
            for r in self.draft.get("dated_components", [])
            if r["id"] == "supplier"
            and r["valid_from"] <= today < r["valid_to"]
            and not r.get("hours")
            and r.get("eligibility", "all") == "all"
        ]
        known = existing[0] if len(existing) == 1 else None
        if known:
            from decimal import Decimal

            from .localization import review_labels

            value = Decimal(str(known["amount"])) * (100 if known["unit"] == "DKK/kWh" else 1)
            labels = await review_labels(self.hass)
            amount_default = {
                "default": format(value, "f").replace(".", labels["decimal_separator"])
            }
        else:
            amount_default = {}
        return await self._simple_form(
            "setup_supplier",
            {
                vol.Optional("amount", **amount_default): money_input(),
                vol.Required(
                    "vat_included", default=known["vat_included"] if known else True
                ): bool,
            },
            "3 / 3",
            user_input,
            errors,
        )

    async def async_step_setup_offers(self, user_input=None):
        if self.draft.get("price_basis") == "all_in":
            return await self._save_step(self.draft, "setup_review", "supplier")
        from .localization import review_labels

        labels = await review_labels(self.hass)
        from .supplier_offers import get_offers

        self._offers = await get_offers(self.hass)
        choices = [(key, key) for key in self._offers] + [
            ("ewii_other", "ewii_other"),
            ("custom", "custom"),
            ("missing", "missing"),
        ]
        if any(
            r["id"] == "supplier" for r in self.draft.get("dated_components", [])
        ) or self.draft.get("provisional_supplier"):
            choices.insert(0, ("keep", "keep"))
        if user_input:
            selected = user_input["product"]
            if selected == "keep":
                return await self._save_step(self.draft, "setup_review", "supplier")
            if selected == "missing":
                return await self._save_step(self.draft, "setup_review", "supplier")
            if selected in self._offers or selected in {"custom", "ewii_other"}:
                return await self._save_step(
                    {
                        **self.draft,
                        "supplier_selection": selected,
                        "supplier": "ewii" if selected.startswith("ewii") else "custom",
                    },
                    "setup_contract",
                    "supplier_selection",
                )
        return await self._simple_form(
            "setup_offers",
            {
                vol.Required(
                    "product", default="keep" if choices[0][0] == "keep" else vol.UNDEFINED
                ): choice(choices, "simple_product")
            },
            "3 / 5",
            user_input,
            availability="" if self._offers else labels.get("offers_unavailable", ""),
        )

    async def async_step_setup_estimate(self, user_input=None):
        errors = {}
        if user_input is not None:
            if not user_input.get("confirm"):
                errors["confirm"] = "confirmation_required"
            else:
                try:
                    amount = decimal_amount(user_input["amount"])
                    site = current_contract(
                        self.draft,
                        amount,
                        user_input["vat_included"],
                        None,
                        True,
                        dt_util.utcnow(),
                        source="user_approved_provisional_NOT_verified",
                    )
                    site["dated_components"] = [
                        r for r in site["dated_components"] if r["id"] != "supplier_subscription"
                    ] + [
                        r
                        for r in self.draft.get("dated_components", [])
                        if r["id"] == "supplier_subscription"
                    ]
                    return await self._save_step(site, "setup_review", "supplier")
                except ValueError, TypeError, KeyError:
                    errors["amount"] = "invalid_decimal"
        estimate = self.draft.get("provisional_supplier", {})
        return await self._simple_form(
            "setup_estimate",
            {
                vol.Required(
                    "amount", **({"default": str(estimate["amount"])} if estimate else {})
                ): money_input(),
                vol.Required("vat_included", default=estimate.get("vat_included", True)): bool,
                vol.Required("confirm", default=False): bool,
            },
            "",
            user_input,
            errors,
        )

    async def async_step_setup_contract(self, user_input=None):
        from .supplier_offers import get_offers

        selected = self.draft.get("supplier_selection", "custom")
        offers = await get_offers(self.hass)
        offer = offers.get(selected)
        if selected not in {"custom", "ewii_other"} and not offer:
            return await self.async_step_setup_offers()
        errors = {}
        if user_input:
            if not user_input.get("confirm"):
                errors["confirm"] = "confirmation_required"
            else:
                try:
                    amount = offer["markup_ore"] if offer else decimal_amount(user_input["amount"])
                    vat_included = (
                        (user_input["vat_basis"] == "included")
                        if offer and offer["vat_included"] is None
                        else offer["vat_included"]
                        if offer
                        else user_input["vat_included"]
                    )
                    monthly = offer["monthly_dkk"] if offer else user_input.get("monthly")
                    site = current_contract(
                        self.draft,
                        amount,
                        vat_included,
                        monthly,
                        user_input.get("estimate", False),
                        dt_util.utcnow(),
                        source=offer["url"] if offer else "user_confirmed_current_supplier",
                        product=selected,
                    )
                    if offer:
                        site["supplier_offer"] = {
                            **offer,
                            "confirmed_at": dt_util.utcnow().isoformat(),
                        }
                    else:
                        site.pop("supplier_offer", None)
                    return await self._save_step(site, "setup_review", "supplier")
                except ValueError, KeyError, TypeError:
                    errors["base"] = "invalid_rate"
        today = str(dt_util.utcnow().astimezone(ZoneInfo(self.draft["timezone"])).date())
        existing = [
            r
            for r in self.draft.get("dated_components", [])
            if r["id"] == "supplier"
            and r["valid_from"] <= today < r["valid_to"]
            and not r.get("hours")
            and r.get("eligibility", "all") == "all"
        ]
        known = existing[0] if len(existing) == 1 else None
        amount_default = {}
        if known:
            from decimal import Decimal

            from .localization import review_labels

            labels = await review_labels(self.hass)
            amount = Decimal(str(known["amount"])) * (100 if known["unit"] == "DKK/kWh" else 1)
            amount_default = {
                "default": format(amount, "f").replace(".", labels["decimal_separator"])
            }
        fields = (
            {}
            if offer
            else {
                vol.Required("amount", **amount_default): money_input(),
                vol.Required(
                    "vat_included", default=known["vat_included"] if known else True
                ): bool,
                vol.Optional("monthly"): number(),
            }
        )
        if offer and offer["vat_included"] is None:
            fields[vol.Required("vat_basis")] = choice(
                [("included", "included"), ("excluded", "excluded")], "vat_basis"
            )
        fields.update(
            {
                vol.Required("estimate", default=False): bool,
                vol.Required("confirm", default=False): bool,
            }
        )
        from .localization import review_labels

        labels = await review_labels(self.hass)
        quote = ""
        if offer:
            markup = f"{offer['markup_ore']:g}".replace(".", labels.get("decimal_separator", "."))
            month = f"{offer['monthly_dkk']:g}".replace(".", labels.get("decimal_separator", "."))
            vat = (
                labels.get("confirm_vat", "Confirm VAT below")
                if offer["vat_included"] is None
                else labels.get("vat_included_label", "Including VAT")
            )
            quote = f"{offer['name']}: **{markup} øre/kWh** · {month} {labels.get('monthly_unit', 'DKK/month')} · {vat}\n\n[EWII]({offer['url']}) · {offer['verified_at'][:10]}"
        return await self._simple_form(
            "setup_contract", fields, "3 / 5", user_input, errors, quote=quote
        )

    async def async_step_setup_tax(self, user_input=None):
        if self.draft.get("price_basis") == "all_in":
            return await self._save_step(self.draft, "setup_review", "tax")
        if user_input:
            if user_input.get("heating"):
                return await self.async_step_setup_heating()
            return await self._save_step(self.draft, "setup_review", "tax")
        return await self._simple_form(
            "setup_tax", {vol.Required("heating", default=False): bool}, "4 / 5", user_input
        )

    async def async_step_setup_heating(self, user_input=None):
        errors = {}
        if user_input:
            if not user_input.get("confirm"):
                errors["confirm"] = "confirmation_required"
            else:
                site = {
                    **self.draft,
                    "heating_registered": True,
                    "usage_year": user_input["year"],
                    "annual_usage_kwh": user_input["usage"],
                    "heating_evidence": "user_confirmed_registration_and_usage",
                }
                return await self._save_step(site, "setup_review", "tax")
        return await self._simple_form(
            "setup_heating",
            {
                vol.Required("year", default=dt_util.utcnow().year): vol.All(
                    vol.Coerce(int), vol.Range(min=2000, max=2100)
                ),
                vol.Required("usage", default=self.draft.get("annual_usage_kwh", 0)): number(),
                vol.Required("confirm", default=False): bool,
            },
            "4 / 5",
            user_input,
            errors,
        )

    async def async_step_setup_review(self, user_input=None):
        from .component_status import review

        self._editing = True
        self.draft = deepcopy(settings(self._wizard_entry))
        summary, _ = await review(self.hass, self._wizard_entry)
        summary["operation"] = getattr(self, "backup_result", "")
        from .localization import review_labels

        labels = await review_labels(self.hass)
        choices = {"setup_check": labels.get("check_prices", "Check prices"), **summary.pop("rows")}
        return self.async_show_menu(
            step_id="setup_review", menu_options=choices, description_placeholders=summary
        )

    async def async_step_setup_spot(self, user_input=None):
        return await self.async_step_setup_site()

    async def async_step_setup_dso(self, user_input=None):
        return await self.async_step_setup_grid()

    async def async_step_setup_net(self, user_input=None):
        return await self.async_step_setup_tax_details()

    async def async_step_setup_system(self, user_input=None):
        return await self.async_step_setup_tax_details()

    async def async_step_setup_electricity_tax(self, user_input=None):
        return await self.async_step_setup_tax_details()

    async def async_step_setup_vat(self, user_input=None):
        return await self.async_step_setup_tax_details()

    async def async_step_setup_final(self, user_input=None):
        return await self.async_step_setup_diagnostics()

    async def async_step_setup_tax_details(self, user_input=None):
        from .component_status import review

        summary, _ = await review(
            self.hass,
            self._wizard_entry,
            details=True,
            only={"energinet_net", "energinet_system", "electricity_tax", "vat"},
        )
        summary.pop("rows", None)
        return self.async_show_menu(
            step_id="setup_tax_details",
            description_placeholders=summary,
            menu_options=["setup_tax", "rates", "setup_review"],
        )

    async def async_step_setup_check(self, user_input=None):
        runtime = self.hass.data.get(DOMAIN, {}).get(self._wizard_entry.entry_id)
        if runtime and getattr(runtime, "settings_current", True):
            await runtime.schedule.startup()
            await runtime.async_refresh()
        else:
            from . import apply_settings

            await apply_settings(
                self.hass, self._wizard_entry, validate_site(settings(self._wizard_entry))
            )
        return await self.async_step_setup_review()

    async def async_step_setup_done(self, user_input=None):
        await self._progress_store.async_save(
            {"next": "setup_review", "saved": getattr(self, "_saved_step", "")}
        )
        return self.async_abort(reason="settings_saved")

    async def async_step_setup_change(self, user_input=None):
        return self.async_show_menu(
            step_id="setup_change",
            menu_options=["setup_site", "setup_grid", "setup_supplier", "setup_tax", "advanced"],
        )

    async def async_step_setup_diagnostics(self, user_input=None):
        from .charging_diagnostics import charging_breakdown
        from .component_status import component_snapshot

        now = dt_util.utcnow()
        selected = getattr(
            self,
            "_selected_quarter",
            now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0),
        )
        snapshot = component_snapshot(self.hass, self._wizard_entry, reference=selected)
        targets = {
            "source": "setup_site",
            "dso": "setup_grid",
            "supplier": "setup_supplier",
            "energinet_net": "setup_tax_details",
            "energinet_system": "setup_tax_details",
            "electricity_tax": "setup_tax_details",
        }
        missing = [
            targets[key]
            for key, row in snapshot["components"].items()
            if key in targets and row["status"] not in {"verified", "included"}
        ]
        return self.async_show_menu(
            step_id="setup_diagnostics",
            description_placeholders={
                "components": await charging_breakdown(self.hass, self._wizard_entry, selected)
            },
            menu_options=list(dict.fromkeys(missing))
            + ["select_quarter", "session_estimate", "setup_review", "advanced"],
        )

    async def async_step_select_quarter(self, user_input=None):
        from .charging_diagnostics import quarter_choices

        choices = quarter_choices(self.hass, self._wizard_entry)
        errors = {}
        if user_input is not None:
            selected = user_input["slot"]
            if selected in dict(choices):
                self._selected_quarter = dt_util.parse_datetime(selected)
                return await self.async_step_setup_diagnostics()
            errors["slot"] = "invalid_quarter"
        return await self._simple_form(
            "select_quarter", {vol.Required("slot"): choice(choices)}, "", user_input, errors
        )

    async def async_step_session_estimate(self, user_input=None):
        from decimal import Decimal

        from .api import ConsumerAPI
        from .charging_cost import estimate_charging_cost
        from .charging_diagnostics import quarter_choices
        from .localization import review_labels

        labels = await review_labels(self.hass)
        errors, result = {}, ""
        choices = quarter_choices(self.hass, self._wizard_entry)
        if user_input is not None:
            try:
                start = dt_util.parse_datetime(user_input["slot"])
                if not start or user_input["slot"] not in dict(choices):
                    raise ValueError("Choose an available quarter")
                from datetime import timedelta

                allocations = [
                    (start + timedelta(minutes=15 * i), line.strip())
                    for i, line in enumerate(user_input["energy"].splitlines())
                ]
                report = estimate_charging_cost(
                    ConsumerAPI(self.hass),
                    self.draft["id"],
                    allocations,
                    energy_kind=user_input["energy_kind"],
                    producer_entry_id=self._wizard_entry.entry_id,
                )
                self._session_report = report
                if report["estimated_cost_dkk"] is None:
                    result = labels["cost_unavailable"]
                else:
                    cost = f"{Decimal(report['estimated_cost_dkk']):.4f}".replace(
                        ".", labels["decimal_separator"]
                    )
                    energy = report["energy_kwh"].replace(".", labels["decimal_separator"])
                    result = f"**{labels['cost_estimate']}: {cost} DKK** · {energy} kWh · {labels['energy_' + report['energy_kind']]}\n\n{labels['marginal_only']}"
            except (ValueError, TypeError, KeyError) as err:
                self._error_detail = str(err)
                if str(err).startswith("Measured energy cannot"):
                    errors["slot"] = "future_measurement"
                else:
                    errors["energy"] = "invalid_energy"
        return await self._simple_form(
            "session_estimate",
            {
                vol.Required("slot"): choice(choices),
                vol.Required("energy"): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                vol.Required("energy_kind", default="planned"): choice(
                    [("planned", "planned"), ("measured", "measured")], "energy_kind"
                ),
            },
            "",
            user_input,
            errors,
            result=result,
        )

    async def async_step_advanced(self, user_input=None):
        return self.async_show_menu(
            step_id="advanced",
            menu_options=[
                "setup_review",
                "rates",
                "source_details",
                "setup_display",
                "setup_offers",
                "setup_estimate",
                "setup_tax_details",
                "storage_tools",
            ],
        )

    async def async_step_rates(self, user_input=None):
        return self.async_show_menu(
            step_id="rates", menu_options=["add_rate", "edit_rate", "remove_rate", "setup_review"]
        )

    async def async_step_storage_tools(self, user_input=None):
        return self.async_show_menu(
            step_id="storage_tools",
            menu_options=[
                "storage",
                "breakdown",
                "site_management",
                "hacs_channel",
                "setup_review",
            ],
        )

    async def async_step_setup_display(self, user_input=None):
        if user_input:
            return await self._save_step({**self.draft, **user_input}, "setup_review", "display")
        return await self._simple_form(
            "setup_display",
            {
                vol.Required(
                    "display_unit", default=self.draft.get("display_unit", "øre/kWh")
                ): choice([("øre/kWh", "øre/kWh"), ("DKK/kWh", "DKK/kWh")])
            },
            "",
            user_input,
        )

    async def async_step_source_details(self, user_input=None):
        from .config_flow import site_schema

        errors = {}
        value = getattr(self, "_source_form", self.draft)
        if user_input:
            changed = {**value, **user_input}
            if changed.get("source_type") != value.get("source_type"):
                self._source_form = changed
                return await self.async_step_source_details()
            try:
                if changed["source_type"] == "nordpool":
                    source = self.hass.config_entries.async_get_entry(
                        changed.get("nordpool_entry", "")
                    )
                    if not source or source.domain != "nordpool":
                        errors["nordpool_entry"] = "source_required"
                    else:
                        await ensure_official_nordpool(self.hass)
                        areas = source.options.get("areas", source.data.get("areas", []))
                        if areas and changed["area"] not in areas:
                            errors["area"] = "unsupported_area"
                    changed.update(price_unit="DKK/MWh", price_basis="spot_ex_vat")
                elif not changed.get("price_entity"):
                    errors["price_entity"] = "entity_required"
                try:
                    await self.hass.async_add_executor_job(ZoneInfo, changed["timezone"])
                except ValueError, ZoneInfoNotFoundError:
                    errors["timezone"] = "invalid_timezone"
                if not errors:
                    return await self._save_step(changed, "setup_review", "site")
            except (ValueError, KeyError, TypeError, ZoneInfoNotFoundError) as err:
                self._error_detail = str(err)
                errors["base"] = "invalid_configuration"
        return self.async_show_form(
            step_id="source_details",
            data_schema=site_schema({**value, **(user_input or {})}),
            errors=errors,
        )

    async def _stage(self, step, changes, schema):
        try:
            return await self._save_step({**self.draft, **changes}, "rates", "advanced")
        except (ValueError, KeyError, TypeError) as err:
            self._error_detail = str(err)
            return self.async_show_form(
                step_id=step, data_schema=schema, errors={"base": "invalid_configuration"}
            )

    async def async_step_remove_rate(self, user_input=None):
        if user_input:
            rules = deepcopy(self.draft.get("dated_components", []))
            rules.pop(int(user_input["rate"]))
            return await self._save_step(
                {**self.draft, "dated_components": rules}, "rates", "advanced"
            )
        return await self._choose("remove_rate", user_input)
