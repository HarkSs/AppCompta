"""Invoices screen placeholder."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class InvoicesView(QWidget):
    """Placeholder for future invoices module."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Factures (à venir)"))
        layout.addStretch()
        self.setLayout(layout)
