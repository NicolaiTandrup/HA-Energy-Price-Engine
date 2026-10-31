"""A consumer requests API2 ranges and exact revisions; no CM fee arithmetic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from custom_components.ha_energy_price_engine.api import EngineNotReady, Status, get_api

from .test_integration import setup


async def test_consumer_exact_site_currency_units_future_readiness_revision_and_unload(
    hass, freezer, price_service
):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    api = get_api(hass, version=2)
    assert api.version == 2
    selected = next(s for s in api.sites() if s.site_id == "home")
    first = datetime(2026, 10, 24, 12, 15, tzinfo=UTC)
    last = first + timedelta(hours=2)
    with (
        patch.object(
            entry.runtime_data.price_engine.database,
            "async_commit",
            side_effect=AssertionError("consumer SQL"),
        ),
        patch.object(
            entry.runtime_data.price_updater,
            "refresh",
            side_effect=AssertionError("consumer fetch"),
        ),
    ):
        window = api.lookup(selected.site_id, first, last)
        assert window.status == Status.READY
        assert (window.site_id, window.currency, window.unit, window.vat_included) == (
            "home",
            "DKK",
            "DKK/kWh",
            True,
        )
        assert window.expected_slots == window.available_slots == len(window.slots) == 8
        assert window.slots[0].start == first and window.slots[-1].end == last
        assert all(a.end == b.start for a, b in zip(window.slots, window.slots[1:]))
        assert window.verified_at <= datetime.now(UTC)
        chosen = tuple((q.start, q.end, q.price) for q in window.slots)
        assert all(amount == pytest.approx(0.31625) for _, _, amount in chosen)
        quote = window.slots[0]
        assert api.revision("home", quote.start, quote.revision) == quote
        assert api.revision("home", quote.start, 99999) is None
    entry.runtime_data.settings_current = False
    unavailable = api.lookup("home", first, last)
    assert unavailable.status == Status.STALE and unavailable.slots == ()
    assert await hass.config_entries.async_unload(entry.entry_id)
    with pytest.raises(EngineNotReady):
        api.lookup("home", first, last)


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-10-24T12:01:00+00:00", "2026-10-24T12:15:00+00:00"),
        ("2026-10-24T12:00:00", "2026-10-24T12:15:00+00:00"),
        ("2026-10-24T12:15:00+00:00", "2026-10-24T12:00:00+00:00"),
    ],
)
async def test_consumer_malformed_range_never_returns_planning_quotes(
    hass, freezer, price_service, start, end
):
    freezer.move_to("2026-10-24T12:07:00Z")
    entry = await setup(hass)
    with pytest.raises(ValueError):
        get_api(hass, 2).lookup("home", datetime.fromisoformat(start), datetime.fromisoformat(end))
    assert await hass.config_entries.async_unload(entry.entry_id)
