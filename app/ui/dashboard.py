"""Dashboard screen."""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.services.reports import ReportService


class DashboardView(QWidget):
    """Simple dashboard showing highlights."""

    def __init__(self, reports: ReportService) -> None:
        super().__init__()
        self.reports = reports
        self.total_label = QLabel()
        self.total_label.setAlignment(Qt.AlignLeft)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Tableau de bord"))
        layout.addWidget(self.total_label)
        layout.addStretch()
        self.setLayout(layout)
        self.refresh()

    def refresh(self) -> None:
        today = date.today()
        start = today.replace(day=1).isoformat()
        end = today.isoformat()
        totals = self.reports.totals_by_period(start, end)
        self.total_label.setText(
            f"Recettes: {totals['recettes']} €\nDépenses: {totals['depenses']} €\nSolde: {totals['solde']} €"
        )
