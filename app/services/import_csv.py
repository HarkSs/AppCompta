"""CSV import services."""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from app.models.entities import Transaction

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CSVMapping:
    date_column: str
    label_column: str
    amount_column: str
    category_id: int
    counterparty_column: str | None = None
    payment_method_column: str | None = None
    note_column: str | None = None
    attachment_column: str | None = None
    invert_amount: bool = False


class CSVImportService:
    """Parse CSV files and convert them to transactions."""

    def __init__(self, delimiter: str = ";", encoding: str = "utf-8") -> None:
        self.delimiter = delimiter
        self.encoding = encoding

    def preview(self, path: Path, limit: int = 20) -> List[Dict[str, str]]:
        with path.open("r", encoding=self.encoding, newline="") as handle:
            reader = csv.DictReader(handle, delimiter=self.delimiter)
            rows: List[Dict[str, str]] = []
            for _, row in zip(range(limit), reader):
                rows.append(row)
            return rows

    def parse(self, path: Path, mapping: CSVMapping) -> List[Transaction]:
        LOGGER.info("Import CSV depuis %s", path)
        transactions: List[Transaction] = []
        with path.open("r", encoding=self.encoding, newline="") as handle:
            reader = csv.DictReader(handle, delimiter=self.delimiter)
            for row in reader:
                amount_raw = row.get(mapping.amount_column, "0").replace(",", ".")
                amount = Decimal(amount_raw)
                if mapping.invert_amount:
                    amount *= Decimal("-1")
                transactions.append(
                    Transaction(
                        id=None,
                        date=row[mapping.date_column],
                        label=row[mapping.label_column],
                        amount=amount,
                        category_id=mapping.category_id,
                        counterparty_id=None,
                        payment_method=row.get(mapping.payment_method_column or "", "")
                        if mapping.payment_method_column
                        else "",
                        note=row.get(mapping.note_column, "") if mapping.note_column else "",
                        attachment=row.get(mapping.attachment_column, None)
                        if mapping.attachment_column
                        else None,
                        reconciled=False,
                        external_ref=None,
                    )
                )
        return transactions


__all__ = ["CSVImportService", "CSVMapping"]
