"""Native, resumable setup. Drafts are durable; active pricing changes only on Save."""

import json
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
from .sources import async_source_defaults, ensure_official_nordpool
from .verification import verify_site


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


class Wizard:
    """Shared creation/options/reconfigure flow; native HA renders every control."""

    _wizard_entry = None
    _wizard_id = None
    _forms = None
    _added = None
    _advanced = False
    _initial = False

    async def _start_wizard(self, entry=None):
        self._wizard_entry = entry
        self._initial = entry is None
        self._wizard_store = Store(
            self.hass, 1, f"{DOMAIN}.wizard.{entry.entry_id if entry else 'initial'}"
        )
        self._forms, self._added = {}, {}
        self._pending = []
        saved = await self._wizard_store.async_load() or {}
        if entry is None:
            existing = {e.unique_id for e in self.hass.config_entries.async_entries(DOMAIN)}
            self._initial_drafts = {
                k: v
                for k, v in saved.items()
                if not (v.get("submitted") and v["draft"].get("id") in existing)
            }
            if self._initial_drafts:
                return self.async_show_form(
                    step_id="wizard_resume",
                    data_schema=vol.Schema(
                        {
                            vol.Required("draft", default=next(iter(self._initial_drafts))): choice(
                                [("new", "➕")]
                                + [
                                    (k, v["draft"].get("name", "…"))
                                    for k, v in self._initial_drafts.items()
                                ]
                            )
                        }
                    ),
                )
            self._wizard_id = uuid4().hex
            self.draft = {
                "source_type": "nordpool",
                "dated_components": [],
                "dso_mode": "manual",
                "vat": 0.25,
                "supplier": "custom",
                "display_unit": "øre/kWh",
            }
            defaults = await async_source_defaults(self.hass)
            self.draft.update(defaults)
            if defaults.get("area") in {"DK1", "DK2"}:
                self.draft["timezone"] = "Europe/Copenhagen"
        else:
            active = settings(entry)
            if saved and saved.get("submitted") and saved.get("draft") == active:
                saved = {}
            self.draft = deepcopy(saved.get("draft", active))
            self._forms = deepcopy(saved.get("forms", {}))
            self._added = deepcopy(saved.get("added", {}))
            self._pending = list(saved.get("pending", []))
            if saved:
                return await getattr(self, "async_step_" + saved.get("step", "wizard_site"))()
        return await self.async_step_wizard_site()

    async def async_step_wizard_resume(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="wizard_resume",
                data_schema=vol.Schema(
                    {
                        vol.Required("draft", default=next(iter(self._initial_drafts))): choice(
                            [("new", "➕")]
                            + [
                                (k, v["draft"].get("name", "…"))
                                for k, v in self._initial_drafts.items()
                            ]
                        )
                    }
                ),
            )
        selected = user_input["draft"]
        if selected == "new":
            self._initial_drafts = {}
            # Preserve other drafts in storage, but start a new independent one.
            self._wizard_id = uuid4().hex
            self.draft = {
                "source_type": "nordpool",
                "dated_components": [],
                "dso_mode": "manual",
                "vat": 0.25,
                "supplier": "custom",
                "display_unit": "øre/kWh",
            }
        else:
            self._wizard_id = selected
            saved = self._initial_drafts[selected]
            self.draft = deepcopy(saved["draft"])
            self._forms = deepcopy(saved.get("forms", {}))
            self._added = deepcopy(saved.get("added", {}))
            self._pending = list(saved.get("pending", []))
            return await getattr(self, "async_step_" + saved.get("step", "wizard_site"))()
        return await self.async_step_wizard_site()

    async def _persist(self, step, submitted=False):
        if self._wizard_entry and not self.hass.config_entries.async_get_entry(
            self._wizard_entry.entry_id
        ):
            return  # An open stale flow cannot resurrect a removed site.
        data = {
            "draft": deepcopy(self.draft),
            "forms": deepcopy(self._forms or {}),
            "added": deepcopy(self._added or {}),
            "step": step,
            "submitted": submitted,
            "pending": list(self._pending),
        }
        if self._initial:
            # Serialize read/modify/write across independent site drafts.
            from asyncio import Lock

            lock = self.hass.data.setdefault(DOMAIN + "_draft_lock", Lock())
            async with lock:
                saved = await self._wizard_store.async_load() or {}
                saved[self._wizard_id] = data
                await self._wizard_store.async_save(saved)
        else:
            await self._wizard_store.async_save(data)

    def _state(self):
        # Human text belongs in native translations, never the system language.
        active = settings(self._wizard_entry) if self._wizard_entry else None
        return "✓" if active == self.draft else "✎"

    async def _verify(self, force=False):
        try:
            site = validate_site(self.draft)
        except ValueError, KeyError, TypeError, ZoneInfoNotFoundError:
            self._site_verified = False
            self._verification = {}
            self._verified_signature = None
            return self._verification
        self._site_verified = True
        signature = json.dumps(site, sort_keys=True)
        if force or getattr(self, "_verified_signature", None) != signature:
            self._verification = await verify_site(
                self.hass,
                site,
                self._wizard_entry.entry_id if self._wizard_entry else "onboarding-preview",
            )
            self._verified_signature = signature
        return self._verification

    def _form(self, step, fields, progress, errors=None):
        fields[vol.Required("navigation", default="next")] = choice(
            [("next", "Next"), ("back", "Back"), ("review", "Review draft")], "wizard_navigation"
        )
        raw = (self._forms or {}).get(step, {})
        optional = {}
        for field, validator in fields.items():
            default = (
                raw.get(field.schema, field.default)
                if field.schema != "navigation"
                else field.default
            )
            optional[vol.Optional(field.schema, default=default)] = validator
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema(optional),
            errors=errors or {},
            last_step=False,
            description_placeholders={
                "draft_status": self._state(),
                "raw": " · ".join(
                    f"{day}: {'✓' if r.get('raw', {}).get('status') == 'READY' else '✕'} {r.get('raw', {}).get('valid_slots', 0)}/{r.get('raw', {}).get('expected_slots', 0)}"
                    for day, r in getattr(self, "_verification", {}).items()
                )
                or "—",
                "progress": progress,
                "context": "",
            },
        )

    async def _remember_error(self, step, data):
        self._forms[step] = deepcopy(data)
        if step not in self._pending:
            self._pending.append(step)
        await self._persist(step)

    async def _back(self, step, data, previous):
        if data is not None and data.get("navigation") == "back":
            self._forms[step] = deepcopy(data)
            if any(k != "navigation" for k in data) and step not in self._pending:
                self._pending.append(step)
            await self._persist(previous)
            return await getattr(self, "async_step_" + previous)()
        return None

    async def _move(self, step, data, next_step, back_step):
        self._forms[step] = deepcopy(data)
        self._pending = [p for p in self._pending if p != step]
        target = {"next": next_step, "back": back_step, "review": "wizard_review"}[
            data.get("navigation", "next")
        ]
        await self._persist(target)
        return await getattr(self, "async_step_" + target)()

    async def async_step_wizard_site(self, user_input=None):
        if result := await self._back("wizard_site", user_input, "wizard_site"):
            return result
        errors = {}
        if user_input is not None:
            name = user_input.get("name", "").strip()
            if not name:
                errors["name"] = "name_required"
            site_id = self.draft.get("id", "")
            if self._initial:
                explicit = user_input.get("id", "").strip()
                used = {e.unique_id for e in self.hass.config_entries.async_entries(DOMAIN)}
                site_id = explicit or slugify(name)[:56] or "site"
                if not explicit:
                    base = site_id
                    counter = 2
                    while site_id in used:
                        site_id = f"{base}_{counter}"
                        counter += 1
                import re

                if not re.fullmatch(r"[a-z0-9][a-z0-9_]{0,63}", site_id):
                    errors["id"] = "invalid_id"
                elif site_id in used:
                    errors["id"] = "duplicate_id"
            if not errors:
                self.draft.update(name=name, id=site_id, source_type=user_input["source_type"])
                return await self._move("wizard_site", user_input, "wizard_source", "wizard_site")
        if errors:
            await self._remember_error("wizard_site", user_input)
        fields = {
            vol.Required("name", default=self.draft.get("name", "")): str,
            vol.Required("source_type", default=self.draft.get("source_type", "nordpool")): choice(
                [
                    ("nordpool", "Official Home Assistant Nord Pool"),
                    ("entity", "Advanced: verified provider entity"),
                ],
                "wizard_source_type",
            ),
        }
        if self._initial:
            fields[vol.Optional("id", default=self.draft.get("id", ""))] = str
        return self._form("wizard_site", fields, "1 / 6", errors)

    async def async_step_wizard_source(self, user_input=None):
        if result := await self._back("wizard_source", user_input, "wizard_site"):
            return result
        from .sources import BASES, UNIT_MULTIPLIERS

        errors = {}
        official = self.draft.get("source_type") == "nordpool"
        if user_input is not None:
            if official:
                entry = self.hass.config_entries.async_get_entry(
                    user_input.get("nordpool_entry", "")
                )
                if entry is None or entry.domain != "nordpool" or entry.disabled_by is not None:
                    errors["nordpool_entry"] = "source_required"
                else:
                    try:
                        await ensure_official_nordpool(self.hass)
                    except ValueError:
                        errors["nordpool_entry"] = "legacy_source"
                if not errors:
                    changed = self.draft.get("nordpool_entry") != entry.entry_id
                    self.draft.update(
                        nordpool_entry=entry.entry_id,
                        price_unit="DKK/MWh",
                        price_basis="spot_ex_vat",
                    )
                    areas = entry.options.get("areas", entry.data.get("areas", []))
                    if (
                        isinstance(areas, list)
                        and areas
                        and (changed or not self.draft.get("area"))
                    ):
                        self.draft["area"] = (
                            "DK2" if "DK2" in areas else areas[0] if len(areas) == 1 else ""
                        )
                        if self.draft["area"] in {"DK1", "DK2"}:
                            self.draft["timezone"] = "Europe/Copenhagen"
            else:
                if not user_input.get("price_entity"):
                    errors["price_entity"] = "source_required"
                if not errors:
                    self.draft.update({k: v for k, v in user_input.items() if k != "navigation"})
                    self.draft["nordpool_entry"] = ""
            if not errors:
                if self._initial and official and self.draft.get("area") in {"DK1", "DK2"}:
                    self.draft.setdefault("danish_public_rates", True)
                return await self._move(
                    "wizard_source", user_input, "wizard_location", "wizard_site"
                )
        if errors:
            await self._remember_error("wizard_source", user_input)
        v = {**self.draft, **(user_input or {})}
        if official:
            fields = {
                vol.Required(
                    "nordpool_entry",
                    **({"default": v["nordpool_entry"]} if v.get("nordpool_entry") else {}),
                ): selector.ConfigEntrySelector(
                    selector.ConfigEntrySelectorConfig(integration="nordpool")
                )
            }
        else:
            fields = {
                vol.Required(
                    "price_entity",
                    **({"default": v["price_entity"]} if v.get("price_entity") else {}),
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required("price_unit", default=v.get("price_unit", "DKK/kWh")): choice(
                    [(k, k.replace("ore", "øre")) for k in UNIT_MULTIPLIERS]
                ),
                vol.Required("price_basis", default=v.get("price_basis", "spot_ex_vat")): choice(
                    list(zip(BASES, BASES)), "price_basis"
                ),
                vol.Required("price_attribute", default=v.get("price_attribute", "slots")): str,
                vol.Required("stale_minutes", default=v.get("stale_minutes", 40)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=2880)
                ),
            }
        return self._form(
            "wizard_source",
            fields,
            "1 / 6",
            errors,
        )

    async def async_step_wizard_location(self, user_input=None):
        if result := await self._back("wizard_location", user_input, "wizard_source"):
            return result
        errors = {}
        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(ZoneInfo, user_input["timezone"])
            except ZoneInfoNotFoundError, ValueError:
                errors["timezone"] = "invalid_timezone"
            area = user_input.get("area", "").strip().upper()
            if not area:
                errors["area"] = "area_required"
            entry = self.hass.config_entries.async_get_entry(self.draft.get("nordpool_entry", ""))
            areas = entry.options.get("areas", entry.data.get("areas", [])) if entry else []
            if areas and area not in areas:
                errors["area"] = "unsupported_area"
            if not errors:
                self.draft.update(
                    area=area,
                    timezone=user_input["timezone"],
                    vat=float(user_input["vat_percent"]) / 100,
                )
                try:
                    validate_site(self.draft)
                except ValueError as e:
                    errors["base"] = "invalid_configuration"
                    self._validation_error = str(e)
                if not errors:
                    await self._verify(force=True)
                    return await self._move(
                        "wizard_location", user_input, "wizard_grid", "wizard_source"
                    )
        if errors:
            await self._remember_error("wizard_location", user_input)
        v = {**self.draft, **(user_input or {})}
        return self._form(
            "wizard_location",
            {
                vol.Required("area", default=v.get("area", "")): str,
                vol.Required("timezone", default=v.get("timezone", "")): str,
                vol.Required(
                    "vat_percent", default=v.get("vat_percent", v.get("vat", 0.25) * 100)
                ): number(0, 100),
            },
            "1 / 6",
            errors,
        )

    async def async_step_wizard_grid(self, user_input=None):
        if result := await self._back("wizard_grid", user_input, "wizard_location"):
            return result
        if user_input is not None:
            if self.draft.get("price_basis") != "all_in":
                self.draft.update({k: v for k, v in user_input.items() if k != "navigation"})
            try:
                validate_site(self.draft)
            except ValueError:
                await self._remember_error("wizard_grid", user_input)
                return self._grid_form({"dso_tariff_class": "invalid_tariff_class"})
            return await self._move("wizard_grid", user_input, "wizard_supplier", "wizard_location")
        return self._grid_form()

    def _grid_form(self, errors=None):
        fields = (
            {}
            if self.draft.get("price_basis") == "all_in"
            else {
                vol.Required("dso_mode", default=self.draft.get("dso_mode", "manual")): choice(
                    [
                        ("radius_c", "Automatic: verified Radius C"),
                        ("manual", "Manual dated grid rates"),
                    ],
                    "wizard_grid_source",
                ),
                vol.Required(
                    "dso_tariff_class", default=self.draft.get("dso_tariff_class", "C")
                ): str,
                vol.Required(
                    "dso_manual_fallback", default=self.draft.get("dso_manual_fallback", False)
                ): bool,
                vol.Required(
                    "dso_stale_days", default=self.draft.get("dso_stale_days", 7)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }
        )
        return self._form(
            "wizard_grid",
            fields,
            "2 / 6",
            errors,
        )

    def _supplier_mode(self):
        if self.draft.get("provisional_supplier"):
            return "provisional"
        if any(r["id"] == "supplier" for r in self.draft.get("dated_components", [])):
            return "retain"
        return "missing"

    def _supplier_fields(self):
        raw = (self._forms or {}).get("wizard_supplier", {})
        fields = {
            vol.Required("supplier", default=self.draft.get("supplier", "custom")): choice(
                [("ewii", "EWII"), ("custom", "Other")], "wizard_supplier"
            ),
            vol.Required(
                "contract_mode", default=raw.get("contract_mode", self._supplier_mode())
            ): choice(
                [(v, v) for v in ("retain", "verified", "provisional", "missing")], "contract_mode"
            ),
            vol.Optional(
                "amount", **({"default": raw["amount"]} if "amount" in raw else {})
            ): number(),
            vol.Required("unit", default=raw.get("unit", "ore/kWh")): choice(
                [("ore/kWh", "øre/kWh"), ("DKK/kWh", "DKK/kWh")]
            ),
            vol.Required("vat_included", default=raw.get("vat_included", False)): bool,
            vol.Required("rate_vat_percent", default=raw.get("rate_vat_percent", 25)): number(
                0, 100
            ),
            **{
                vol.Optional(
                    k, **({"default": raw[k]} if raw.get(k) else {})
                ): selector.DateSelector()
                for k in ("valid_from", "valid_to")
            },
            vol.Optional("contract_reference", default=raw.get("contract_reference", "")): str,
            vol.Required("confirm_verified", default=raw.get("confirm_verified", False)): bool,
            vol.Required("approve_estimate", default=raw.get("approve_estimate", False)): bool,
            vol.Required("replace_periods", default=raw.get("replace_periods", False)): bool,
        }
        return fields

    def _apply_supplier(self, data):
        mode = data.get("contract_mode", "missing")
        # Preserve the prior programmatic flow contract without rendering its old
        # implementation fields. Explicit date/reference is the old assertion.
        legacy = "add_contract" in data
        if legacy:
            mode = "verified" if data["add_contract"] else "retain"
        self.draft["supplier"] = data.get("supplier", self.draft.get("supplier", "custom"))
        if mode == "retain":
            return {}
        if mode == "missing":
            self.draft.pop("provisional_supplier", None)
            return {}
        errors = {
            k: "rate_required"
            for k in ("amount", "valid_from", "valid_to")
            if k not in data or data[k] in (None, "")
        }
        if legacy and mode == "verified":
            errors.update(
                {k: "rate_required" for k in ("source", "verified_on") if not data.get(k)}
            )
        if mode == "verified" and not (
            data.get("confirm_verified")
            or (legacy and data.get("verified_on") and data.get("source"))
        ):
            errors["confirm_verified"] = "verification_required"
        if mode == "provisional" and not data.get("approve_estimate"):
            errors["approve_estimate"] = "estimate_approval_required"
        if errors:
            return errors
        today = str(dt_util.utcnow().astimezone(ZoneInfo(self.draft["timezone"])).date())
        period = {k: data[k] for k in ("amount", "unit", "vat_included", "valid_from", "valid_to")}
        period["vat_rate"] = float(data["rate_vat_percent"]) / 100
        if mode == "provisional":
            period.update(approved=True, approved_on=today)
            try:
                validate_site({**self.draft, "provisional_supplier": period})
            except ValueError, KeyError, TypeError:
                return {"base": "invalid_rate"}
            self.draft["provisional_supplier"] = period
            return {}
        rule = {
            **period,
            "id": "supplier",
            "locked": True,
            "eligibility": "all",
            "verified_on": data.get("verified_on", today),
            "source": data.get("source")
            or data.get("contract_reference")
            or "user_confirmed_bill_or_contract",
        }
        rules = deepcopy(self.draft.get("dated_components", []))
        prior = (self._added or {}).get("supplier")
        if prior in rules:
            rules.remove(prior)
        if data.get("replace_periods"):
            retained = []
            for old in rules:
                if (
                    old["id"] != "supplier"
                    or old["valid_to"] <= rule["valid_from"]
                    or old["valid_from"] >= rule["valid_to"]
                ):
                    retained.append(old)
                    continue
                if old["valid_from"] < rule["valid_from"]:
                    retained.append({**old, "valid_to": rule["valid_from"]})
                if old["valid_to"] > rule["valid_to"]:
                    retained.append({**old, "valid_from": rule["valid_to"]})
            rules = retained
        try:
            validate_site({**self.draft, "dated_components": [*rules, rule]})
        except ValueError, KeyError, TypeError:
            return {"base": "invalid_rate"}
        self.draft["dated_components"] = [*rules, rule]
        self.draft.pop("provisional_supplier", None)
        self._added["supplier"] = rule
        return {}

    async def async_step_wizard_supplier(self, user_input=None):
        if result := await self._back("wizard_supplier", user_input, "wizard_grid"):
            return result
        errors = {}
        if user_input is not None:
            if self.draft.get("price_basis") != "all_in":
                errors = self._apply_supplier(user_input)
            if not errors:
                return await self._move(
                    "wizard_supplier", user_input, "wizard_charges", "wizard_grid"
                )
            await self._remember_error("wizard_supplier", user_input)
        result = self._form(
            "wizard_supplier",
            {} if self.draft.get("price_basis") == "all_in" else self._supplier_fields(),
            "3 / 6",
            errors,
        )
        result["data_schema"].extra = vol.ALLOW_EXTRA
        return result

    async def async_step_wizard_charges(self, user_input=None):
        if result := await self._back("wizard_charges", user_input, "wizard_supplier"):
            return result
        if user_input is not None:
            if self.draft.get("price_basis") != "all_in":
                self.draft.update({k: v for k, v in user_input.items() if k != "navigation"})
            return await self._move(
                "wizard_charges", user_input, "wizard_display", "wizard_supplier"
            )
        fields = (
            {}
            if self.draft.get("price_basis") == "all_in"
            else {
                vol.Required(
                    "danish_public_rates", default=self.draft.get("danish_public_rates", False)
                ): bool,
                vol.Required(
                    "heating_registered", default=self.draft.get("heating_registered", False)
                ): bool,
                vol.Required(
                    "annual_usage_kwh", default=self.draft.get("annual_usage_kwh", 0)
                ): number(),
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
        return self._form(
            "wizard_charges",
            fields,
            "4 / 6",
        )

    async def async_step_wizard_display(self, user_input=None):
        if result := await self._back("wizard_display", user_input, "wizard_charges"):
            return result
        if user_input is not None:
            self.draft["display_unit"] = user_input["display_unit"]
            return await self._move("wizard_display", user_input, "wizard_review", "wizard_charges")
        return self._form(
            "wizard_display",
            {
                vol.Required(
                    "display_unit", default=self.draft.get("display_unit", "øre/kWh")
                ): choice([("øre/kWh", "øre/kWh"), ("DKK/kWh", "DKK/kWh")])
            },
            "5 / 6",
        )

    def _review(self):
        site = self.draft
        reports = getattr(self, "_verification", {})

        def mark(ok):
            return "✓" if ok else "✕"

        result = {
            "draft_status": self._state(),
            "site_validation": mark(getattr(self, "_site_verified", False)),
            "pending": str(len(self._pending)),
            "name": site.get("name", ""),
            "site_id": site.get("id", ""),
            "area": site.get("area", ""),
            "timezone": site.get("timezone", ""),
            "display_unit": site.get("display_unit", "øre/kWh"),
            "vat": str(site.get("vat", 0.25) * 100),
            "review": "",
        }
        source = self.hass.config_entries.async_get_entry(site.get("nordpool_entry", ""))
        result["source"] = source.title if source else site.get("price_entity", "—")
        result["raw"] = "\n\n".join(
            f"{d}: {mark(r.get('raw', {}).get('status') == 'READY')} {r.get('raw', {}).get('valid_slots', 0)}/{r.get('raw', {}).get('expected_slots', 0)}"
            for d, r in reports.items()
        )
        result["final"] = "\n\n".join(
            f"{d}: {mark(r.get('status') == 'READY')} {r.get('calculated_slots', 0)}/{r.get('raw', {}).get('expected_slots', 0)}"
            for d, r in reports.items()
        )
        for key in ("supplier", "dso", "energinet_net", "energinet_system", "electricity_tax"):
            result[key] = "; ".join(
                f"{d}: {mark(r.get('coverage', {}).get(key, True) or (key == 'dso' and r.get('failure_stage') not in {'source', 'grid'} and site.get('dso_mode') == 'radius_c'))}"
                for d, r in reports.items()
            )
        result["technical"] = (
            "\n\n".join(
                f"{d}: "
                + (
                    str(r.get("affected_period", d)) + " · " + ", ".join(r["missing_components"])
                    if r.get("missing_components")
                    else r["reason"]
                )
                for d, r in reports.items()
                if r.get("reason")
            )
            or "—"
        )
        return result

    async def _compact_review(self):
        from .localization import review_labels
        from .price_components import danish_public_components

        labels = await review_labels(self.hass)

        def label(key):
            return labels.get(key, key)

        reports = getattr(self, "_verification", {})
        days = list(reports)
        rules = list(self.draft.get("dated_components", []))
        if self.draft.get("danish_public_rates"):
            rules += danish_public_components()
        keys = (
            "source",
            "dso",
            "supplier",
            "energinet_net",
            "energinet_system",
            "electricity_tax",
            "final",
        )
        statuses = {}
        for key in keys:
            statuses[key] = []
            for day, report in reports.items():
                if key == "source":
                    raw = report.get("raw", {})
                    state = (
                        "verified"
                        if raw.get("status") == "READY"
                        else "expired"
                        if raw.get("status") == "STALE"
                        else "unavailable"
                    )
                elif key == "final":
                    state = (
                        "verified"
                        if report.get("status") == "READY" and report.get("calculated_slots", 0)
                        else "provisional"
                        if report.get("estimated_slots", 0)
                        else "missing"
                    )
                elif self.draft.get("price_basis") == "all_in":
                    state = "included"
                elif report.get("coverage", {}).get(key) or (
                    key == "dso"
                    and report.get("grid_status") == "READY"
                    and self.draft.get("dso_mode") == "radius_c"
                ):
                    state = "verified"
                elif key == "supplier" and report.get("estimated_slots", 0):
                    state = "provisional"
                elif any(r["id"] == key and r["valid_to"] <= day for r in rules):
                    state = "expired"
                else:
                    state = (
                        "unavailable"
                        if key == "dso" and report.get("failure_stage") == "grid"
                        else "missing"
                    )
                statuses[key].append(state)
        headers = [
            f"{label('today' if i == 0 else 'tomorrow')} {day}" for i, day in enumerate(days)
        ]
        table = "| | " + " | ".join(headers) + " |\n|---|" + "---|" * len(days)
        for key in keys:
            table += (
                "\n| " + label(key) + " | " + " | ".join(label(v) for v in statuses[key]) + " |"
            )
        result = self._review()
        result["table"] = table
        options = ["wizard_save"]
        for key, step in (
            ("source", "wizard_source"),
            ("dso", "wizard_grid"),
            ("supplier", "wizard_supplier"),
        ):
            if any(v not in {"verified", "included"} for v in statuses[key]):
                options.append(step)
        if any(
            v not in {"verified", "included"}
            for key in ("energinet_net", "energinet_system", "electricity_tax")
            for v in statuses[key]
        ):
            options.append("wizard_charges")
        return result, options + ["wizard_display", "advanced"]

    async def async_step_wizard_review(self, user_input=None):
        await self._persist("wizard_review")
        await self._verify()
        summary, options = await self._compact_review()
        return self.async_show_menu(
            step_id="wizard_review",
            description_placeholders=summary,
            menu_options=options,
        )

    async def async_step_wizard_recheck(self, user_input=None):
        await self._verify(force=True)
        return await self.async_step_wizard_review()

    async def async_step_wizard_save(self, user_input=None):
        if self._pending:
            result = await getattr(self, "async_step_" + self._pending[0])()
            result["errors"] = {"base": "pending_page"}
            return result
        try:
            site = validate_site(self.draft)
        except ValueError, KeyError, TypeError, ZoneInfoNotFoundError:
            return self._form(
                "wizard_location",
                {
                    vol.Required("area", default=self.draft.get("area", "")): str,
                    vol.Required("timezone", default=self.draft.get("timezone", "")): str,
                    vol.Required("vat_percent", default=self.draft.get("vat", 0.25) * 100): number(
                        0, 100
                    ),
                },
                "1 / 6",
                {"base": "invalid_configuration"},
            )
        if site["source_type"] == "nordpool":
            entry = self.hass.config_entries.async_get_entry(site["nordpool_entry"])
            if entry is None or entry.domain != "nordpool":
                return await self.async_step_wizard_source({"nordpool_entry": ""})
            try:
                await ensure_official_nordpool(self.hass)
            except ValueError:
                return await self.async_step_wizard_source(
                    {"nordpool_entry": site["nordpool_entry"]}
                )
        await self._verify(force=True)
        summary = self._review()
        await self._persist("wizard_review", submitted=True)
        if self._initial:
            if any(
                e.unique_id == site["id"] for e in self.hass.config_entries.async_entries(DOMAIN)
            ):
                return self._form(
                    "wizard_site",
                    {
                        vol.Required("name", default=site["name"]): str,
                        vol.Required("id", default=site["id"]): str,
                        vol.Required("source_type", default=site["source_type"]): choice(
                            [("nordpool", "Official Nord Pool"), ("entity", "Provider entity")]
                        ),
                    },
                    "1 / 6",
                    {"id": "duplicate_id"},
                )
            await self.async_set_unique_id(site["id"])
            return self.async_create_entry(
                title=site["name"],
                data=site,
                description="saved_pending_verification",
                description_placeholders=summary,
            )
        from . import apply_settings

        await apply_settings(self.hass, self._wizard_entry, site)
        if not self._actually_ready():
            return await self._saved_form()
        if hasattr(self, "async_set_unique_id"):
            return self.async_abort(reason="reconfigure_successful")
        # Options already applied and verified above; None prevents a second update.
        return self.async_create_entry(title="", data=None)

    def _actually_ready(self):
        from .api import ConsumerAPI, Status
        from .price_engine import day_bounds

        entry = self._wizard_entry
        runtime = self.hass.data.get(DOMAIN, {}).get(entry.entry_id) if entry else None
        if runtime is None:
            return False
        now = dt_util.utcnow()
        day = now.astimezone(ZoneInfo(runtime.site["timezone"])).date()
        result = ConsumerAPI(self.hass).lookup(
            runtime.site["id"], *day_bounds(day, runtime.site["timezone"])
        )
        return result.status == Status.READY and bool(result.records)

    async def _saved_form(self):
        # Readiness is from the loaded, persisted runtime, never the draft preview.
        entry = self._wizard_entry
        runtime = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
        reports = runtime.schedule.days.get(runtime.site["id"], {}) if runtime else {}
        if runtime:
            from datetime import date

            from .verification import component_coverage

            self._verification = {
                day: {
                    **report,
                    "raw": runtime.price_updater.raw_reports.get(day, {}),
                    "coverage": component_coverage(runtime.site, date.fromisoformat(day)),
                    "calculated_slots": report.get("valid_slots", 0)
                    if report.get("status") == "READY"
                    else 0,
                    "estimated_slots": len(runtime.price_updater.estimated_slots.get(day, ())),
                }
                for day, report in reports.items()
            }
        summary, choices = await self._compact_review()
        choices = [v for v in choices if v != "wizard_save"] + ["finish"]
        await self._persist("wizard_saved", submitted=True)
        return self.async_show_form(
            step_id="wizard_saved",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default=choices[0]): choice(
                        [(v, v) for v in choices], "saved_action"
                    )
                }
            ),
            description_placeholders=summary,
        )

    async def async_step_wizard_saved(self, user_input=None):
        if user_input is None:
            return await self._saved_form()
        if user_input["action"] == "finish":
            return self.async_abort(reason="saved_incomplete")
        return await getattr(self, "async_step_" + user_input["action"])()

    async def async_on_create_entry(self, result):
        self._wizard_entry = result["result"]
        self._initial = False
        self._wizard_store = Store(self.hass, 1, f"{DOMAIN}.wizard.{self._wizard_entry.entry_id}")
        if self._actually_ready():
            return result
        return await self._saved_form()

    async def async_step_wizard_discard(self, user_input=None):
        if user_input and user_input.get("confirm"):
            if self._initial:
                saved = await self._wizard_store.async_load() or {}
                saved.pop(self._wizard_id, None)
                await self._wizard_store.async_save(saved)
            else:
                await self._wizard_store.async_save({})
            return self.async_abort(reason="draft_discarded")
        return self.async_show_form(
            step_id="wizard_discard",
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
            description_placeholders={"draft_status": self._state()},
        )

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
                    vol.Required("operation", default="archive"): choice(
                        [("archive", "archive"), ("permanent", "permanent")], "site_removal"
                    ),
                    vol.Optional("site_id", default=""): str,
                    vol.Required("confirm", default=False): bool,
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
