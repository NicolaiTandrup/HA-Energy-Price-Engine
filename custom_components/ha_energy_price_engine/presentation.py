"""Presentation only: canonical prices and energy costs keep their full precision."""

from decimal import ROUND_HALF_UP, Decimal


def display_precision(unit):
    return 2 if unit == "øre/kWh" else 4


def display_value(value, unit):
    return value * (100 if unit == "øre/kWh" else 1) if value is not None else None


def format_price(value, unit="øre/kWh", decimal_separator=".", *, from_ore=False):
    """Fixed locale-aware monetary text; never feed this result back into pricing."""
    if value is None:
        return "—"
    amount = Decimal(str(value))
    if from_ore:
        amount /= 100
    if unit == "øre/kWh":
        amount *= 100
    precision = display_precision(unit)
    amount = amount.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)
    if not amount:
        amount = abs(amount)
    return format(amount, f".{precision}f").replace(".", decimal_separator)
