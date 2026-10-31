"""Native flow manager saves accepted steps and never infers private money."""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.ha_energy_price_engine.api import Status, get_api
from custom_components.ha_energy_price_engine.configuration import settings
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.status import statistics


async def begin(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["step_id"] == "site"
    assert {str(k) for k in result["data_schema"].schema} == {"name", "nordpool_entry"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Example site", "nordpool_entry": "np"}
    )
    assert result["step_id"] == "grid"
    return result, hass.config_entries.async_entries(DOMAIN)[0]


async def test_interruption_wrong_decimal_saved_steps_and_from_now_stats(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    result, entry = await begin(hass)
    sid = entry.data["id"]
    hass.config_entries.flow.async_abort(result["flow_id"])
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "grid"
    fid = result["flow_id"]
    result = await hass.config_entries.options.async_configure(fid, {"grid": "manual"})
    assert result["step_id"] == "grid_rate" and settings(entry)["setup_step"] == "grid_rate"
    result = await hass.config_entries.options.async_configure(
        fid, {"amount": "20", "vat_included": False}
    )
    assert result["step_id"] == "supplier"
    result = await hass.config_entries.options.async_configure(
        fid, {"amount": "11..1", "vat_included": False}
    )
    assert result["errors"]["amount"] == "invalid_amount"
    assert all(r["id"] != "supplier" for r in settings(entry)["dated_components"])
    result = await hass.config_entries.options.async_configure(
        fid, {"amount": "3,75", "vat_included": True}
    )
    assert result["step_id"] == "review"
    assert set(result["menu_options"]) == {
        "done",
        "check",
        "site",
        "grid",
        "supplier",
        "advanced",
        "reset",
    }
    start = datetime(2026, 10, 24, 12, 15, tzinfo=UTC)
    assert get_api(hass).lookup(sid, start, start + timedelta(minutes=15)).status == Status.READY
    facts = statistics(entry.runtime_data)
    assert (
        facts["scope"] == "remaining_day" and facts["used_slots"] == 39 and facts["day_slots"] == 96
    )
    assert facts["average"] == pytest.approx(0.31625)
    hass.config_entries.options.async_abort(fid)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "review" and settings(entry)["id"] == sid
    await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "done"})
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_explicit_whole_day_confirmation_yields_immediate_full_day(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    result, entry = await begin(hass)
    fid = result["flow_id"]
    await hass.config_entries.flow.async_configure(fid, {"grid": "manual"})
    await hass.config_entries.flow.async_configure(
        fid, {"amount": "20", "vat_included": False, "whole_day": True}
    )
    result = await hass.config_entries.flow.async_configure(
        fid, {"amount": "3", "vat_included": False, "whole_day": True}
    )
    assert result["step_id"] == "review"
    facts = statistics(entry.runtime_data)
    assert facts["scope"] == "full_day" and facts["used_slots"] == 96
    assert facts["minimum"] == facts["maximum"] == facts["average"] == pytest.approx(0.31625)
    await hass.config_entries.flow.async_configure(fid, {"next_step_id": "done"})
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_reset_requires_exact_name_and_explicit_confirm(hass, freezer, price_service):
    freezer.move_to("2026-10-24T12:07:00Z")
    result, entry = await begin(hass)
    hass.config_entries.flow.async_abort(result["flow_id"])
    hass.config_entries.async_update_entry(
        entry, options={**settings(entry), "setup_step": "review"}
    )
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    fid = result["flow_id"]
    result = await hass.config_entries.options.async_configure(fid, {"next_step_id": "reset"})
    result = await hass.config_entries.options.async_configure(
        fid, {"name": "wrong", "confirm": True}
    )
    assert result["errors"]["base"] == "confirm_reset"
    defaults = {str(k): k.default() for k in result["data_schema"].schema}
    assert defaults == {"name": "wrong", "confirm": True}
    assert hass.config_entries.async_get_entry(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        fid, {"name": "Example site", "confirm": True}
    )
    assert result["reason"] == "site_reset"


async def test_advanced_rates_and_saved_grid_choice_resume(hass, freezer, price_service):
    from .helpers import model
    from .test_integration import setup

    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass, model(dated_components=[]))
    result = await hass.config_entries.options.async_init(entry.entry_id)
    fid = result["flow_id"]
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "grid"})
    result = await hass.config_entries.options.async_configure(fid, {"grid": "manual"})
    assert result["step_id"] == "grid_rate" and settings(entry)["setup_step"] == "grid_rate"
    hass.config_entries.options.async_abort(fid)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "grid_rate"
    fid = result["flow_id"]
    await hass.config_entries.options.async_configure(
        fid, {"amount": "20", "vat_included": False, "whole_day": True}
    )
    result = await hass.config_entries.options.async_configure(
        fid, {"amount": "3", "vat_included": False, "whole_day": True}
    )
    # A resumed edit can complete supplier or return straight to the saved review.
    if result["step_id"] == "supplier":
        result = await hass.config_entries.options.async_configure(
            fid, {"amount": "3", "vat_included": False, "whole_day": True}
        )
    assert result["step_id"] == "review"
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "advanced"})
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "add_rate"})
    fields = {
        "component": "energinet_net",
        "amount": "8",
        "vat_included": False,
        "vat_rate": 0.25,
        "valid_from": "2026-10-24",
        "valid_to": "2027-01-01",
        "hours": ["17", "18"],
        "source": "Explicit fictional owner confirmation",
        "confirm": False,
    }
    result = await hass.config_entries.options.async_configure(fid, fields)
    assert result["errors"]["base"] == "invalid_rate"
    result = await hass.config_entries.options.async_configure(fid, {**fields, "confirm": True})
    assert result["step_id"] == "review"
    assert settings(entry)["dated_components"][-1]["id"] == "energinet_net"
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "advanced"})
    await hass.config_entries.options.async_configure(fid, {"next_step_id": "remove_rate"})
    result = await hass.config_entries.options.async_configure(
        fid, {"rate": str(len(settings(entry)["dated_components"]) - 1)}
    )
    assert result["step_id"] == "review"
    assert all(r["id"] != "energinet_net" for r in settings(entry)["dated_components"])
    hass.config_entries.options.async_abort(fid)
    assert await hass.config_entries.async_unload(entry.entry_id)
