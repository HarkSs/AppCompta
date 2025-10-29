"""Transactions screen."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.entities import Transaction
from app.services.categories import CategoryService
from app.services.transactions import TransactionService


class TransactionsView(QWidget):
    """Allow listing and adding transactions."""

    def __init__(self, tx_service: TransactionService, category_service: CategoryService) -> None:
        super().__init__()
        self.tx_service = tx_service
        self.category_service = category_service
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Libellé", "Montant", "Catégorie", "Paiement", "Tiers", "Note"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        self.label_edit = QLineEdit()
        self.amount_edit = QLineEdit()
        self.category_combo = QComboBox()
        self.payment_edit = QLineEdit()
        self.counterparty_edit = QLineEdit()
        self.note_edit = QTextEdit()
        self.attachment_edit = QLineEdit()
        attach_btn = QPushButton("…")
        attach_btn.clicked.connect(self.select_attachment)

        form_layout = QFormLayout()
        form_layout.addRow("Date", self.date_edit)
        form_layout.addRow("Libellé", self.label_edit)
        form_layout.addRow("Montant", self.amount_edit)
        form_layout.addRow("Catégorie", self.category_combo)
        form_layout.addRow("Mode de paiement", self.payment_edit)
        form_layout.addRow("Tiers", self.counterparty_edit)
        form_layout.addRow("Note", self.note_edit)
        attach_layout = QHBoxLayout()
        attach_layout.addWidget(self.attachment_edit)
        attach_layout.addWidget(attach_btn)
        form_layout.addRow("Pièce jointe", attach_layout)
        save_btn = QPushButton("Ajouter")
        save_btn.clicked.connect(self.save_transaction)
        form_layout.addRow(save_btn)

        splitter = QSplitter()
        table_container = QWidget()
        table_layout = QVBoxLayout()
        table_layout.addWidget(self.table)
        table_container.setLayout(table_layout)
        splitter.addWidget(table_container)
        form_container = QWidget()
        form_container.setLayout(form_layout)
        splitter.addWidget(form_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout = QVBoxLayout()
        main_layout.addWidget(QLabel("Transactions"))
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self.load_categories()
        self.refresh()

    def load_categories(self) -> None:
        self.category_combo.clear()
        for cat in self.category_service.list_categories():
            self.category_combo.addItem(cat.name, cat.id)

    def refresh(self) -> None:
        transactions = self.tx_service.list_transactions()
        self.table.setRowCount(len(transactions))
        for row_idx, tx in enumerate(transactions):
            self.table.setItem(row_idx, 0, QTableWidgetItem(tx.date))
            self.table.setItem(row_idx, 1, QTableWidgetItem(tx.label))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"{tx.amount:.2f}"))
            category_name = self.category_combo.itemText(
                self.category_combo.findData(tx.category_id)
            )
            self.table.setItem(row_idx, 3, QTableWidgetItem(category_name))
            self.table.setItem(row_idx, 4, QTableWidgetItem(tx.payment_method))
            self.table.setItem(row_idx, 5, QTableWidgetItem(""))
            self.table.setItem(row_idx, 6, QTableWidgetItem(tx.note))

    def save_transaction(self) -> None:
        amount = Decimal(self.amount_edit.text().replace(",", "."))
        tx = Transaction(
            id=None,
            date=self.date_edit.date().toString("yyyy-MM-dd"),
            label=self.label_edit.text(),
            amount=amount,
            category_id=self.category_combo.currentData(),
            counterparty_id=None,
            payment_method=self.payment_edit.text(),
            note=self.note_edit.toPlainText(),
            attachment=self.attachment_edit.text() or None,
        )
        self.tx_service.create_transaction(tx)
        self.refresh()
        self.label_edit.clear()
        self.amount_edit.clear()
        self.payment_edit.clear()
        self.counterparty_edit.clear()
        self.note_edit.clear()
        self.attachment_edit.clear()

    def select_attachment(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier")
        if file_path:
            self.attachment_edit.setText(file_path)
