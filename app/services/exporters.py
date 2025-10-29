"""Export services."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.db.database import Database
from app.models.entities import Transaction


@dataclass(slots=True)
class Period:
    start: str
    end: str


class ExportService:
    """Generate CSV and PDF exports."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def export_all_transactions(self, path: Path) -> None:
        rows = self.db.query(
            """
            SELECT t.date, t.label, t.amount, c.name as categorie, cp.name as tiers,
                   t.payment_method, t.note, t.attachment, t.reconciled, t.external_ref
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            LEFT JOIN counterparties cp ON cp.id = t.counterparty_id
            ORDER BY t.date ASC
            """
        )
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "date",
                    "libellé",
                    "montant",
                    "catégorie",
                    "tiers",
                    "mode_paiement",
                    "note",
                    "pièce_jointe",
                    "rapproché",
                    "référence_externe",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row["date"],
                        row["label"],
                        f"{row['amount']:.2f}",
                        row["categorie"],
                        row["tiers"],
                        row["payment_method"],
                        row["note"],
                        row["attachment"],
                        row["reconciled"],
                        row["external_ref"],
                    ]
                )

    def export_livre_recettes_csv(self, path: Path, period: Period | None = None) -> None:
        rows = self._livre_query(period)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "Date",
                    "Numéro",
                    "Client",
                    "Libellé",
                    "Montant TTC",
                    "Mode de paiement",
                    "Référence",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row["date"],
                        row["number"] or "",
                        row["client"] or "",
                        row["label"],
                        f"{row['amount']:.2f}",
                        row["payment_method"],
                        row["external_ref"] or "",
                    ]
                )

    def export_livre_recettes_pdf(self, path: Path, period: Period | None = None) -> None:
        rows = list(self._livre_query(period))
        pdf = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        y = height - 40
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, y, "Livre des recettes")
        y -= 30
        pdf.setFont("Helvetica", 10)
        headers = ["Date", "Numéro", "Client", "Libellé", "Montant TTC", "Paiement", "Référence"]
        pdf.drawString(40, y, " | ".join(headers))
        y -= 20
        for row in rows:
            line = " | ".join(
                [
                    row["date"],
                    row["number"] or "",
                    (row["client"] or "")[:18],
                    row["label"][:28],
                    f"{row['amount']:.2f}",
                    row["payment_method"][:12],
                    (row["external_ref"] or "")[:12],
                ]
            )
            if y < 60:
                pdf.showPage()
                y = height - 60
            pdf.drawString(40, y, line)
            y -= 18
        pdf.save()

    def _livre_query(self, period: Period | None):
        if period:
            return self.db.query(
                """
                SELECT t.date, i.number, cp.name as client, t.label, t.amount,
                       t.payment_method, t.external_ref
                FROM transactions t
                LEFT JOIN invoices i ON i.id = t.external_ref
                LEFT JOIN counterparties cp ON cp.id = t.counterparty_id
                WHERE t.date BETWEEN ? AND ? AND t.amount > 0
                ORDER BY t.date ASC
                """,
                (period.start, period.end),
            )
        return self.db.query(
            """
            SELECT t.date, i.number, cp.name as client, t.label, t.amount,
                   t.payment_method, t.external_ref
            FROM transactions t
            LEFT JOIN invoices i ON i.id = t.external_ref
            LEFT JOIN counterparties cp ON cp.id = t.counterparty_id
            WHERE t.amount > 0
            ORDER BY t.date ASC
            """
        )


__all__ = ["ExportService", "Period"]
