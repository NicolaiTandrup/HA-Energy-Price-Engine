"""Native discovery, generic source contract, site lifecycle and upgrades."""

from copy import deepcopy
from datetime import UTC, date, datetime

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine import async_migrate_entry
from custom_components.ha_energy_price_engine.api import get_api
from custom_components.ha_energy_price_engine.configuration import validate_site
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.repairs import async_create_fix_flow
from custom_components.ha_energy_price_engine.sources import source_defaults

from .test_integration import model, price_service, setup  # noqa: F401
from .test_price_engine import rows
from .wizard_helpers import options_advanced, source_page


async def test_official_discovery_requires_confirmation_when_ambiguous(hass):
    assert source_defaults(hass) == {}
    first = MockConfigEntry(domain="nordpool", data={"areas": ["DK1"]}, title="One")
    first.add_to_hass(hass)
    assert source_defaults(hass) == {"nordpool_entry": first.entry_id, "area": "DK1"}
    second = MockConfigEntry(domain="nordpool", data={"areas": ["DK2"]}, title="Two")
    second.add_to_hass(hass)
    assert source_defaults(hass) == {}
    form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    schema = form["data_schema"].schema
    assert not any(
        str(k) == "nordpool_entry" and callable(k.default) and k.default() for k in schema
    )


def entity_site():
    return {
        **model(),
        "source_type": "entity",
        "nordpool_entry": "",
        "price_entity": "sensor.provider",
        "price_unit": "DKK/MWh",
        "price_basis": "spot_ex_vat",
        "price_attribute": "slots",
        "stale_minutes": 40,
    }


def entity_attributes(now, **changes):
    data = []
    for day in (date(2026, 10, 23), date(2026, 10, 24)):
        data.extend(
            {"start": s.start.isoformat(), "end": s.end.isoformat(), "price": -100}
            for s in rows(day)
        )
    return {
        "slots": data,
        "currency": "DKK",
        "unit_of_measurement": "DKK/MWh",
        "vat_included": False,
        "verified_at": now.isoformat(),
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"currency": "EUR"},
        {"unit_of_measurement": "DKK/kWh"},
        {"vat_included": True},
        {"vat_included": "false"},
        {"verified_at": "2026-10-25T00:00:00Z"},
        {"verified_at": "2026-10-22T00:00:00Z"},
        {"verified_at": "unknown"},
    ],
)
async def test_generic_source_without_official_integration_and_explicit_conventions(
    hass, freezer, changes
):
    freezer.move_to("2026-10-23T12:00:00Z")
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    hass.states.async_set("sensor.provider", "-100", entity_attributes(now, **changes))
    entry = await setup(hass, entity_site())
    result = get_api(hass).lookup("home", rows()[0].start, rows()[-1].end, now=now)
    if changes:
        assert str(result.status) == "ERROR" and not result.records
    else:
        assert str(result.status) == "READY" and len(result.records) == 96
        assert result.records[0].final_price_incl_vat == pytest.approx(
            (-0.1 + 0.2 + 0.043 + 0.072 + 0.008 + 0.11) * 1.25
        )
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_all_in_entity_does_not_apply_vat_twice(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    data = entity_site()
    data.update(price_basis="all_in", dated_components=[], danish_public_rates=False)
    attrs = entity_attributes(now, vat_included=True)
    hass.states.async_set("sensor.provider", "-100", attrs)
    entry = await setup(hass, data)
    assert entry.runtime_data.price_engine.records["home"][0].final_price_incl_vat == -0.1
    with pytest.raises(ValueError, match="All-in"):
        validate_site({**data, "dated_components": model()["dated_components"]})
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_upgrade_preserves_rates_and_refuses_future_entry_versions(hass):
    data = model()
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=deepcopy(data),
        options={"dated_components": deepcopy(data["dated_components"])},
        version=1,
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 3 and entry.data["source_type"] == "nordpool"
    assert entry.options["dated_components"] == data["dated_components"]
    assert not hass.data.get(DOMAIN)  # Upgrade does not start sources or alter history.
    future = MockConfigEntry(domain=DOMAIN, data=data, version=99)
    future.add_to_hass(hass)
    assert not await async_migrate_entry(hass, future)


@pytest.mark.usefixtures("price_service")
async def test_reconfigure_and_remove_keep_identity_and_other_site(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    np = MockConfigEntry(domain="nordpool", entry_id="np", state=ConfigEntryState.LOADED)
    np.add_to_hass(hass)
    home = await setup(hass)
    away = await setup(hass, model("away"))
    config = deepcopy(dict(home.data))
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": home.entry_id}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Renamed", "source_type": "nordpool"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"nordpool_entry": "np"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"area": "DK2", "timezone": "Europe/Copenhagen", "vat_percent": 25, "navigation": "review"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "wizard_save"}
    )
    await hass.async_block_till_done()
    assert result["type"] == "abort" and result["reason"] == "reconfigure_successful"
    assert (
        home.options["id"] == config["id"]
        and home.options["dated_components"] == config["dated_components"]
    )
    assert home.title == "Renamed"
    assert (await hass.config_entries.async_remove(home.entry_id))["require_restart"] is False
    assert {s.site_id for s in get_api(hass).sites()} == {"away"}
    assert await hass.config_entries.async_unload(away.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_repairs_recheck_does_not_dismiss_unverified_prices(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    data = model()
    data["dated_components"] = []
    entry = await setup(hass, data)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, entry.entry_id)
    assert issue.is_fixable
    flow = await async_create_fix_flow(hass, entry.entry_id, issue.data)
    flow.hass = hass
    result = await flow.async_step_confirm({})
    assert result["errors"]["base"] == "pricing_not_ready"
    assert ir.async_get(hass).async_get_issue(DOMAIN, entry.entry_id) is not None
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_arbitrary_site_count_isolation_and_supplier_label_not_a_rate(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    entries = []
    for i in range(7):
        data = model(f"site_{i}")
        data["supplier"] = "ewii"
        if i == 6:
            data["dated_components"] = []
        entries.append(await setup(hass, data))
    assert len(get_api(hass).sites()) == 7
    assert entries[-1].runtime_data.data["status"] == "INCOMPLETE"
    assert all(e.runtime_data.data["status"] == "READY" for e in entries[:-1])
    for e in entries:
        assert await hass.config_entries.async_unload(e.entry_id)


@pytest.mark.usefixtures("price_service")
async def test_native_verified_backup_and_supplier_label_do_not_mutate_rates(hass, freezer):
    freezer.move_to("2026-10-23T12:00:00Z")
    entry = await setup(hass)
    before = entry.runtime_data.price_engine.records["home"]
    flow = await options_advanced(hass, entry.entry_id)
    fid = flow["flow_id"]
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "storage"})
    result = await hass.config_entries.options.async_configure(fid, {})
    assert result["type"] == "menu"
    assert "✓ .storage/" in result["description_placeholders"]["draft_status"]
    assert list(entry.runtime_data.price_engine.database.path.parent.glob("*.backup-*"))
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "wizard_supplier"})
    result = await hass.config_entries.options.async_configure(
        fid, {"supplier": "ewii", "navigation": "review"}
    )
    assert result["type"] == "menu"
    assert entry.runtime_data.price_engine.records["home"] == before
    assert not entry.options  # Both editor actions leave saved business rates unchanged.
    hass.config_entries.options.async_abort(fid)
    assert await hass.config_entries.async_unload(entry.entry_id)


def test_unverified_radius_class_and_boolean_money_rejected():
    data = model()
    with pytest.raises(ValueError, match="Only Radius C"):
        validate_site({**data, "dso_mode": "radius_c", "dso_tariff_class": "B"})
    for field in ("amount", "vat_rate"):
        changed = deepcopy(data)
        changed["dated_components"][0][field] = True
        with pytest.raises(ValueError, match="Boolean"):
            validate_site(changed)


async def test_legacy_hacs_domain_is_never_discovered_as_official_nordpool(hass):
    from pytest_homeassistant_custom_component.common import MockModule, mock_integration

    from custom_components.ha_energy_price_engine.sources import async_source_defaults

    mock_integration(hass, MockModule("nordpool"), built_in=False)
    MockConfigEntry(domain="nordpool", entry_id="legacy", data={"areas": ["DK2"]}).add_to_hass(hass)
    assert await async_source_defaults(hass) == {}
    result = await source_page(hass, "Legacy test")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"nordpool_entry": "legacy"}
    )
    assert result["errors"]["nordpool_entry"] == "legacy_source"
