"""Reports screen."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.reports import ReportService


class ReportsView(QWidget):
    """Display simple summaries."""

    def __init__(self, reports: ReportService) -> None:
        super().__init__()
        self.reports = reports
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Catégorie", "Total"])
        refresh_btn = QPushButton("Actualiser")
        refresh_btn.clicked.connect(self.refresh)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Rapports"))
        layout.addWidget(refresh_btn)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.refresh()

    def refresh(self) -> None:
        today = date.today()
        start = today.replace(day=1).isoformat()
        end = today.isoformat()
        items = self.reports.totals_by_category(start, end)
        self.table.setRowCount(len(items))
        for row_idx, (name, total) in enumerate(items):
            self.table.setItem(row_idx, 0, QTableWidgetItem(name or ""))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f"{total:.2f}"))
