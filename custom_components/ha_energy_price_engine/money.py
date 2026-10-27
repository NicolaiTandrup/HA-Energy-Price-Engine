"""Lossless ordinary money input; canonical prices remain numeric DKK/kWh."""

import re
from decimal import Decimal, InvalidOperation
from math import isfinite


def decimal_amount(value):
    """Accept a decimal point or comma, never guess thousands separators."""
    if isinstance(value, bool):
        raise ValueError("Enter a non-negative decimal amount")
    text = str(value).strip()
    if not re.fullmatch(r"\d+(?:[.,]\d+)?", text):
        raise ValueError("Enter a non-negative decimal amount")
    try:
        amount = Decimal(text.replace(",", "."))
    except InvalidOperation as err:
        raise ValueError("Enter a non-negative decimal amount") from err
    if not amount.is_finite() or not isfinite(float(amount)):
        raise ValueError("Enter a finite decimal amount")
    return format(amount.normalize(), "f")


def per_kwh(amount, unit):
    """Convert decimal øre without an intermediate binary division/rounding."""
    return float(Decimal(str(amount)) / (100 if unit == "ore/kWh" else 1))
