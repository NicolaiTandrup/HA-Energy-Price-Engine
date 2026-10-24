"""Pinned machine fixtures through real producer and both actual consumer decoders."""

import importlib
import json
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from jsonschema import Draft202012Validator, FormatChecker
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_energy_price_engine.api import get_api, serialize_result
from custom_components.ha_energy_price_engine.const import DOMAIN
from custom_components.ha_energy_price_engine.models import PriceSlot
from custom_components.ha_energy_price_engine.price_engine import PriceEngine
from tools.prepare_consumer_refs import PINS

ROOT = Path(__file__).parents[1]
SCHEMA = json.loads((ROOT / "docs/contracts/price-api-v1.schema.json").read_text())
CASES = json.loads((ROOT / "docs/contracts/price-api-v1.examples.json").read_text())["scenarios"]


def consumer_module(name):
    reference = ROOT / "consumer-references" / name
    assert (reference / "SOURCE_COMMIT").read_text().strip() == PINS[name], (
        "Run tools/prepare_consumer_refs.py"
    )
    alias = "pe_consumer_reference_" + name
    if alias not in sys.modules:
        package = ModuleType(alias)
        package.__path__ = [str(reference / "custom_components/ev_charge_manager")]
        sys.modules[alias] = package
    return importlib.import_module(alias + ".price_consumer")


@pytest.mark.parametrize("case", CASES, ids=lambda x: x["name"])
@pytest.mark.parametrize("consumer", ["pr15", "pr16"])
async def test_actual_consumer_matches_pinned_machine_snapshot_without_io(hass, case, consumer):
    request, response = case["request"], case["response"]
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=request["producer_entry_id"],
        data={"id": "synthetic"},
        state=ConfigEntryState.LOADED,
    )
    entry.add_to_hass(hass)
    engine = PriceEngine(hass, entry.entry_id)
    now = datetime.fromisoformat(request["now"])
    slots = [
        PriceSlot(
            datetime.fromisoformat(s["start"]),
            datetime.fromisoformat(s["end"]),
            s["final_price_incl_vat"],
        )
        for s in response["slots"]
    ]
    await engine.async_update(
        "synthetic", slots, {"mode": "all_in"}, {"verified_at": now.isoformat()}, now
    )
    c = SimpleNamespace(
        site={
            "id": "synthetic",
            "name": "Synthetic",
            "area": "DK2",
            "timezone": "Europe/Copenhagen",
        },
        price_engine=engine,
        schedule=SimpleNamespace(
            days={
                "synthetic": {
                    case["name"][:10]: {
                        "status": response["status"],
                        "last_success": now.isoformat(),
                    }
                }
            }
        ),
    )
    hass.data[DOMAIN] = {entry.entry_id: c}
    start, end = datetime.fromisoformat(request["start"]), datetime.fromisoformat(request["end"])
    api = get_api(hass)
    payload = serialize_result(api.lookup("synthetic", start, end, now=now))
    Draft202012Validator(SCHEMA, format_checker=FormatChecker()).validate(payload)
    assert payload == response
    with (
        patch(
            "custom_components.ha_energy_price_engine.price_engine.calculate",
            side_effect=AssertionError("read arithmetic"),
        ),
        patch.object(engine.database, "async_load", side_effect=AssertionError("read DB")),
        patch.object(engine.database, "async_commit", side_effect=AssertionError("read write")),
    ):
        decoder = consumer_module(consumer).PriceConsumer(hass)
        if consumer == "pr15":
            result = decoder.lookup("synthetic", start, end, now)
            actual = result.slots
            assert result.status == response["status"]
        else:
            site = {
                "producer_entry": entry.entry_id,
                "producer_site": "synthetic",
                "id": "consumer",
                "timezone": "Europe/Copenhagen",
            }
            if response["status"] != "READY":
                with pytest.raises(ValueError, match="INCOMPLETE"):
                    decoder.lookup(site, start, end, now)
                return
            actual = decoder.lookup(site, start, end, now)
        expected = slots if response["status"] == "READY" else []
        assert [(x.start, x.end, x.price) for x in actual] == [
            (x.start, x.end, x.price) for x in expected
        ]
    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)


def test_schema_rejects_wrong_money_vat_and_timestamp():
    from copy import deepcopy

    validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
    for key, value in [
        ("currency", "EUR"),
        ("vat_included", False),
        ("unit", "ore/kWh"),
        ("verified_at", "not-a-date"),
        ("api_version", True),
    ]:
        wrong = deepcopy(CASES[0]["response"])
        wrong[key] = value
        assert list(validator.iter_errors(wrong))
