from __future__ import annotations

from decimal import Decimal

from app.models.entities import Transaction
from app.services.reconciliation import reconcile


def test_reconcile_matches_same_amount() -> None:
    transactions = [
        Transaction(id=1, date="2024-01-01", label="A", amount=Decimal("100.00"), category_id=1,
                    counterparty_id=None, payment_method="", note="", attachment=None),
        Transaction(id=2, date="2024-01-02", label="B", amount=Decimal("100.02"), category_id=1,
                    counterparty_id=None, payment_method="", note="", attachment=None),
    ]
    matched = reconcile(transactions, Decimal("0.05"))
    assert 2 in matched or 1 in matched
