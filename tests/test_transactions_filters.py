from __future__ import annotations

from decimal import Decimal

from app.db.database import Database, create_schema
from app.models.entities import Transaction
from app.services.transactions import TransactionService


def test_list_transactions_with_filters(tmp_path):
    db = Database(tmp_path / "test.db")
    create_schema(db)
    service = TransactionService(db)

    service.create_transaction(
        Transaction(
            id=None,
            date="2026-01-10",
            label="Cotisation janvier",
            amount=Decimal("120.00"),
            category_id=1,
            counterparty_id=None,
            payment_method="Virement",
            note="",
            attachment=None,
        )
    )
    service.create_transaction(
        Transaction(
            id=None,
            date="2026-02-03",
            label="Achat matériel",
            amount=Decimal("-40.50"),
            category_id=2,
            counterparty_id=None,
            payment_method="Carte",
            note="Masques",
            attachment=None,
        )
    )

    results = service.list_transactions(start_date="2026-02-01", end_date="2026-02-28")
    assert len(results) == 1
    assert results[0].label == "Achat matériel"

    by_category = service.list_transactions(category_id=1)
    assert len(by_category) == 1
    assert by_category[0].label == "Cotisation janvier"

    by_search = service.list_transactions(search="masques")
    assert len(by_search) == 1
    assert by_search[0].label == "Achat matériel"

    db.close()
