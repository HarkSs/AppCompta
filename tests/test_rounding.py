from __future__ import annotations

from decimal import Decimal

from app.models.entities import Transaction


def test_decimal_quantize_two_decimals() -> None:
    amount = Decimal("10.1234").quantize(Decimal("0.01"))
    assert amount == Decimal("10.12")
