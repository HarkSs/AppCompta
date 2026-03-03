"""Service layer for transactions."""
from __future__ import annotations

import logging
from dataclasses import asdict
from decimal import Decimal
from typing import Iterable, List

from app.db.database import Database
from app.models.entities import Transaction

LOGGER = logging.getLogger(__name__)


class TransactionService:
    """Provide CRUD for transactions."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def list_transactions(
        self,
        limit: int = 200,
        offset: int = 0,
        start_date: str | None = None,
        end_date: str | None = None,
        category_id: int | None = None,
        search: str | None = None,
    ) -> List[Transaction]:
        conditions: list[str] = []
        params: list[object] = []
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)
        if category_id is not None:
            conditions.append("category_id = ?")
            params.append(category_id)
        if search:
            conditions.append("(label LIKE ? OR note LIKE ? OR payment_method LIKE ?)")
            like_value = f"%{search}%"
            params.extend([like_value, like_value, like_value])

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        rows = self.db.query(
            f"""
            SELECT id, date, label, amount, category_id, counterparty_id, payment_method,
                   note, attachment, reconciled, external_ref
            FROM transactions
            {where_clause}
            ORDER BY date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, limit, offset]),
        )
        return [self._row_to_transaction(row) for row in rows]

    def create_transaction(self, transaction: Transaction) -> int:
        LOGGER.info("Création transaction %s", transaction.label)
        cur = self.db.execute(
            """
            INSERT INTO transactions(
                date, label, amount, category_id, counterparty_id, payment_method,
                note, attachment, reconciled, external_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction.date,
                transaction.label,
                float(transaction.amount),
                transaction.category_id,
                transaction.counterparty_id,
                transaction.payment_method,
                transaction.note,
                transaction.attachment,
                int(transaction.reconciled),
                transaction.external_ref,
            ),
        )
        return int(cur.lastrowid)

    def update_transaction(self, transaction: Transaction) -> None:
        if transaction.id is None:
            raise ValueError("Transaction sans identifiant")
        LOGGER.info("Mise à jour transaction %s", transaction.id)
        self.db.execute(
            """
            UPDATE transactions SET
                date=?, label=?, amount=?, category_id=?, counterparty_id=?,
                payment_method=?, note=?, attachment=?, reconciled=?, external_ref=?
            WHERE id=?
            """,
            (
                transaction.date,
                transaction.label,
                float(transaction.amount),
                transaction.category_id,
                transaction.counterparty_id,
                transaction.payment_method,
                transaction.note,
                transaction.attachment,
                int(transaction.reconciled),
                transaction.external_ref,
                transaction.id,
            ),
        )

    def delete_transaction(self, transaction_id: int) -> None:
        LOGGER.info("Suppression transaction %s", transaction_id)
        self.db.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))

    def bulk_insert(self, transactions: Iterable[Transaction]) -> None:
        to_insert = [
            (
                t.date,
                t.label,
                float(t.amount),
                t.category_id,
                t.counterparty_id,
                t.payment_method,
                t.note,
                t.attachment,
                int(t.reconciled),
                t.external_ref,
            )
            for t in transactions
        ]
        if to_insert:
            LOGGER.info("Insertion en lot de %s transactions", len(to_insert))
            self.db.executemany(
                """
                INSERT INTO transactions(
                    date, label, amount, category_id, counterparty_id, payment_method,
                    note, attachment, reconciled, external_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                to_insert,
            )

    def mark_reconciled(self, transaction_ids: Iterable[int]) -> None:
        ids = list(transaction_ids)
        if not ids:
            return
        LOGGER.info("Marquage rapproché pour %s transactions", len(ids))
        placeholders = ",".join("?" for _ in ids)
        self.db.execute(
            f"UPDATE transactions SET reconciled=1 WHERE id IN ({placeholders})",
            tuple(ids),
        )

    def _row_to_transaction(self, row) -> Transaction:
        return Transaction(
            id=row["id"],
            date=row["date"],
            label=row["label"],
            amount=Decimal(str(row["amount"])),
            category_id=row["category_id"],
            counterparty_id=row["counterparty_id"],
            payment_method=row["payment_method"],
            note=row["note"],
            attachment=row["attachment"],
            reconciled=bool(row["reconciled"]),
            external_ref=row["external_ref"],
        )


__all__ = ["TransactionService"]
