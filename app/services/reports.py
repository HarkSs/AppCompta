"""Reporting utilities."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple

from app.db.database import Database


class ReportService:
    """Compute aggregated data for dashboard and reports."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def totals_by_period(self, start: str, end: str) -> Dict[str, Decimal]:
        rows = self.db.query(
            """
            SELECT SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as recettes,
                   SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as depenses,
                   SUM(amount) as solde
            FROM transactions
            WHERE date BETWEEN ? AND ?
            """,
            (start, end),
        )
        row = rows[0]
        return {
            "recettes": Decimal(str(row["recettes"] or 0)).quantize(Decimal("0.01")),
            "depenses": Decimal(str(row["depenses"] or 0)).quantize(Decimal("0.01")),
            "solde": Decimal(str(row["solde"] or 0)).quantize(Decimal("0.01")),
        }

    def totals_by_category(self, start: str, end: str) -> List[Tuple[str, Decimal]]:
        rows = self.db.query(
            """
            SELECT c.name, SUM(t.amount) as total
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.date BETWEEN ? AND ?
            GROUP BY c.name
            ORDER BY total DESC
            """,
            (start, end),
        )
        return [(row["name"], Decimal(str(row["total"] or 0))) for row in rows]

    def monthly_balance(self, year: str) -> List[Tuple[str, Decimal]]:
        rows = self.db.query(
            """
            SELECT substr(date, 1, 7) as month, SUM(amount) as total
            FROM transactions
            WHERE substr(date, 1, 4) = ?
            GROUP BY month
            ORDER BY month
            """,
            (year,),
        )
        return [(row["month"], Decimal(str(row["total"] or 0))) for row in rows]


__all__ = ["ReportService"]
