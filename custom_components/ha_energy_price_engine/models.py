"""Price-only UTC types ported from EV Charge Manager; no vehicle coupling."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isfinite

QUARTER = timedelta(minutes=15)


def utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class PriceSlot:
    start: datetime
    end: datetime
    price: float


def validate_slots(slots: list[PriceSlot]) -> list[PriceSlot]:
    result = sorted(
        (PriceSlot(utc(s.start), utc(s.end), s.price) for s in slots), key=lambda s: s.start
    )
    for i, slot in enumerate(result):
        if not isfinite(slot.price) or slot.end - slot.start != QUARTER:
            raise ValueError("Prices must be finite, non-overlapping 15-minute intervals")
        if i and result[i - 1].end > slot.start:
            raise ValueError("Overlapping price intervals")
    return result
