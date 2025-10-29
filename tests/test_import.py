from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.services.import_csv import CSVImportService, CSVMapping


def test_import_parsing(tmp_path: Path) -> None:
    csv_content = "date;libelle;montant\n2024-01-01;Test;123.45\n"
    file_path = tmp_path / "import.csv"
    file_path.write_text(csv_content, encoding="utf-8")
    service = CSVImportService()
    mapping = CSVMapping(
        date_column="date",
        label_column="libelle",
        amount_column="montant",
        category_id=1,
    )
    transactions = service.parse(file_path, mapping)
    assert len(transactions) == 1
    assert transactions[0].amount == Decimal("123.45")

def test_import_invert_amount(tmp_path: Path) -> None:
    csv_content = "date;libelle;montant\n2024-01-01;Test;-50\n"
    file_path = tmp_path / "import_neg.csv"
    file_path.write_text(csv_content, encoding="utf-8")
    service = CSVImportService()
    mapping = CSVMapping(
        date_column="date",
        label_column="libelle",
        amount_column="montant",
        category_id=1,
        invert_amount=True,
    )
    transactions = service.parse(file_path, mapping)
    assert transactions[0].amount == Decimal("50")
