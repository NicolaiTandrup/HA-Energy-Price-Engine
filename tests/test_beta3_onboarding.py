"""Functional beta.3 acceptance: actual runtime vs raw source and canonical math."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.models import PriceSlot
from custom_components.ha_energy_price_engine.price_engine import day_bounds
from custom_components.ha_energy_price_engine.update import release_for
from custom_components.ha_energy_price_engine.verification import verify_site

from .test_integration import model, price_service, setup  # noqa:F401


async def grid(site, start, end, now):
    rows = []
    while start < end:
        rows.append(PriceSlot(start, start + timedelta(minutes=15), 0.2))
        start += timedelta(minutes=15)
    return rows, {"provider": "SYNTHETIC verified Radius fixture", "verified_at": now.isoformat()}


@pytest.mark.parametrize("day,count", [("2026-10-23", 96), ("2026-10-25", 100), ("2026-03-29", 92)])
@pytest.mark.usefixtures("price_service")
async def test_complete_runtime_and_preview_on_normal_and_dst_days(hass, freezer, day, count):
    freezer.move_to(day + "T10:00:00Z")
    data = model()
    data["dso_mode"] = "radius_c"
    data["dated_components"] = [r for r in data["dated_components"] if r["id"] != "dso"]
    MockConfigEntry(domain="nordpool", entry_id="np", state=ConfigEntryState.LOADED).add_to_hass(
        hass
    )
    # model's explicit fictional supplier is .11; source fixture is -.1; public .123.
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get", side_effect=grid
    ):
        entry = await setup(hass, data)
        result = get_api(hass).lookup(
            "home",
            *day_bounds(datetime.fromisoformat(day).date()),
            now=datetime.fromisoformat(day + "T10:00:00+00:00"),
        )
        assert str(result.status) == "READY" and len(result.records) == count
        assert all(
            r.final_price_incl_vat
            == pytest.approx((-0.1 + 0.2 + 0.11 + 0.043 + 0.072 + 0.008) * 1.25)
            for r in result.records
        )
        c = entry.runtime_data
        assert c.price_updater.raw_reports[day]["valid_slots"] == count
        assert all(s.price == -0.1 for s in c.price_updater.raw_slots[day])
        preview = await verify_site(hass, c.site)
        assert preview[day]["calculated_slots"] == count
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("missing", ["supplier", "energinet_net", "electricity_tax"])
@pytest.mark.usefixtures("price_service")
async def test_missing_component_never_hides_valid_source(hass, freezer, missing):
    from custom_components.ha_energy_price_engine.price_components import danish_public_components

    freezer.move_to("2026-10-23T12:00:00Z")
    data = model()
    data["danish_public_rates"] = False
    data["dated_components"] = [
        r for r in data["dated_components"] + danish_public_components() if r["id"] != missing
    ]
    entry = await setup(hass, data)
    c = entry.runtime_data
    assert c.data["status"] == "INCOMPLETE" and c.data["failure_stage"] == "configuration"
    assert missing in c.data["missing_components"] and "2026-10-23" in c.data["affected_period"]
    assert c.price_updater.raw_reports["2026-10-23"]["status"] == "READY"
    assert c.price_updater.raw_reports["2026-10-23"]["valid_slots"] == 96
    assert c.data["valid_slots"] == 0
    assert not c.price_engine.records.get("home")
    assert (
        hass.states.get(
            er.async_get(hass).async_get_entity_id(
                "sensor", "ha_energy_price_engine", "home_display_raw_current_ore"
            )
        ).state
        == "-10.0"
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_radius_failure_keeps_raw_and_identifies_grid(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    data = model()
    data["dso_mode"] = "radius_c"
    data["dated_components"] = [r for r in data["dated_components"] if r["id"] != "dso"]
    with patch(
        "custom_components.ha_energy_price_engine.tariff_source.TariffSource.get",
        side_effect=ValueError("Radius tariff coverage unavailable"),
    ):
        entry = await setup(hass, data)
        c = entry.runtime_data
        assert c.data["failure_stage"] == "grid" and "Radius" in c.data["reason"]
        assert c.price_updater.raw_reports["2026-10-23"]["status"] == "READY"
        assert c.data["valid_slots"] == 0 and not c.price_engine.records.get("home")
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_ledger_failure_does_not_hide_spot_source(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    with patch(
        "custom_components.ha_energy_price_engine.ledger.LedgerDatabase.async_commit",
        side_effect=OSError("Disk full"),
    ):
        entry = await setup(hass)
        c = entry.runtime_data
        assert c.data["failure_stage"] == "storage" and "Disk full" in c.data["reason"]
        assert c.price_updater.raw_reports["2026-10-23"]["status"] == "READY"
        assert not c.price_engine.records.get("home")
        assert await hass.config_entries.async_unload(entry.entry_id)


def test_release_channels_never_offer_commit_or_draft():
    data = [
        {"tag_name": "56cdb3c", "prerelease": False},
        {"tag_name": "v0.0.8-preview.1", "prerelease": False},
        {"tag_name": "v0.1.0-beta.3", "prerelease": True},
        {"tag_name": "v0.1.0-beta.4", "prerelease": True, "draft": True},
        {"tag_name": "v0.0.9", "prerelease": False},
    ]
    assert release_for(data, "0.1.0-beta.2")["tag_name"] == "v0.1.0-beta.3"
    assert release_for(data, "0.1.0") is None
    assert release_for([{"tag_name": "v9.0.0-preview.1", "prerelease": False}], "0.1.0") is None
    assert release_for(data, "0.1.0-beta.3")["tag_name"] == "v0.1.0-beta.3"


async def test_review_before_completing_site_does_not_crash_or_certify(hass):
    from custom_components.ha_energy_price_engine.const import DOMAIN

    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"name": "Unfinished", "nordpool_entry": "missing"}
    )
    assert (
        result["step_id"] == "setup_site"
        and result["errors"]["nordpool_entry"] == "source_required"
    )
    assert not hass.config_entries.async_entries(DOMAIN)
    hass.config_entries.flow.async_abort(flow["flow_id"])


async def test_native_translations_follow_requested_locale_and_fall_back(hass):
    import json
    from pathlib import Path

    from homeassistant.helpers.translation import async_get_translations

    from custom_components.ha_energy_price_engine.const import DOMAIN

    root = Path(__file__).parents[1] / "custom_components" / DOMAIN
    en = json.loads((root / "translations/en.json").read_text())
    da = json.loads((root / "translations/da.json").read_text())

    def keys(value, prefix=""):
        return {prefix + k for k, v in value.items() if not isinstance(v, dict)} | set().union(
            *(keys(v, prefix + k + ".") for k, v in value.items() if isinstance(v, dict))
        )

    assert keys(en) == keys(da)
    # Core resolves native resources per request, independent from system geography.
    hass.config.language = "en"
    english = await async_get_translations(hass, "en", "config", {DOMAIN})
    danish = await async_get_translations(hass, "da", "config", {DOMAIN})
    unknown = await async_get_translations(hass, "zz", "config", {DOMAIN})
    key = f"component.{DOMAIN}.config.step.wizard_supplier.title"
    assert english[key] == "3 / 6 · Supplier contract"
    assert danish[key] == "3 / 6 · Leverandørkontrakt"
    assert unknown[key] == english[key]


@pytest.mark.parametrize("failure", ["partial", "outage"])
async def test_source_degradation_is_independent_and_not_old_component_error(
    hass,
    freezer,
    price_service,  # noqa: F811
    failure,
):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    c = entry.runtime_data
    before = c.price_engine.records["home"]
    if failure == "partial":
        price_service["partial"] = True
    else:
        hass.services.async_remove("nordpool", "get_prices_for_date")
    await c.schedule.startup()
    await c.async_refresh()
    report = c.price_updater.raw_reports["2026-10-23"]
    assert report["status"] == ("INCOMPLETE" if failure == "partial" else "STALE")
    assert c.data["status"] != "READY"
    assert not c.data.get("missing_components")
    assert c.data["failure_stage"] == "source"
    from custom_components.ha_energy_price_engine.status import source_status

    status = source_status(c)
    assert status["stored_slots"] == 96 and status["verified_final_slots"] == 0
    assert status["raw_status"] == report["status"]
    assert c.price_engine.records["home"] == before
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_review_coverage_matches_canonical_heating_and_spring_missing_hour(hass, freezer):
    from custom_components.ha_energy_price_engine.price_components import danish_public_components

    freezer.move_to("2026-03-29T10:00:00Z")
    data = model()
    data.update(
        danish_public_rates=False, heating_registered=True, annual_usage_kwh=5000, usage_year=2026
    )
    data["dated_components"] += danish_public_components()
    for rule in data["dated_components"]:
        rule["hours"] = [hour for hour in range(24) if hour != 2]
        if rule["id"] == "electricity_tax":
            rule["eligibility"] = "heating_above_4000"
    result = (await verify_site(hass, data))["2026-03-29"]
    assert result["calculated_slots"] == 92 and all(result["coverage"].values())
    data["heating_registered"] = False
    result = (await verify_site(hass, data))["2026-03-29"]
    assert result["calculated_slots"] == 0 and not result["coverage"]["electricity_tax"]
