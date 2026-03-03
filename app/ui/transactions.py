"""Transactions screen."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from app.services.settings import SettingsService
from app.services.transactions import TransactionService


class TransactionsView(QWidget):
    """Allow listing and adding transactions."""

    def __init__(
        self,
        tx_service: TransactionService,
        category_service: CategoryService,
        settings_service: SettingsService,
    ) -> None:
        super().__init__()
        self.tx_service = tx_service
        self.category_service = category_service
        self.settings_service = settings_service

        self.filter_start = QDateEdit()
        self.filter_start.setCalendarPopup(True)
        self.filter_start.setDisplayFormat("dd/MM/yyyy")
        self.filter_end = QDateEdit()
        self.filter_end.setCalendarPopup(True)
        self.filter_end.setDisplayFormat("dd/MM/yyyy")
        self.filter_category = QComboBox()
        self.filter_search = QLineEdit()
        self.filter_search.setPlaceholderText("Recherche (libellé, note, paiement)")
        filter_btn = QPushButton("Filtrer")
        filter_btn.clicked.connect(self.refresh)
        reset_btn = QPushButton("Réinitialiser")
        reset_btn.clicked.connect(self.reset_filters)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Date", "Libellé", "Montant", "Catégorie", "Paiement", "Tiers", "Note"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setDate(date.today())
        self.label_edit = QLineEdit()
        self.amount_edit = QLineEdit()
        self.category_combo = QComboBox()
        self.payment_edit = QLineEdit()
        self.counterparty_edit = QLineEdit()
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(72)
        self.attachment_edit = QLineEdit()
        attach_btn = QPushButton("…")
        attach_btn.clicked.connect(self.select_attachment)

        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
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
        delete_btn = QPushButton("Supprimer la sélection")
        delete_btn.clicked.connect(self.delete_selected_transaction)
        form_layout.addRow(save_btn)
        form_layout.addRow(delete_btn)

        splitter = QSplitter()
        table_container = QWidget()
        table_layout = QVBoxLayout()
        filters_layout = QHBoxLayout()
        filters_layout.addWidget(QLabel("Du"))
        filters_layout.addWidget(self.filter_start)
        filters_layout.addWidget(QLabel("Au"))
        filters_layout.addWidget(self.filter_end)
        filters_layout.addWidget(QLabel("Catégorie"))
        filters_layout.addWidget(self.filter_category)
        filters_layout.addWidget(self.filter_search, stretch=1)
        filters_layout.addWidget(filter_btn)
        filters_layout.addWidget(reset_btn)
        table_layout.addLayout(filters_layout)
        table_layout.addWidget(self.table)
        table_container.setLayout(table_layout)
        splitter.addWidget(table_container)
        form_container = QWidget()
        form_container.setLayout(form_layout)
        splitter.addWidget(form_container)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)

        main_layout = QVBoxLayout()
        main_layout.addWidget(QLabel("Transactions"))
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self._configure_shortcuts()
        self.load_categories()
        self.restore_filters()
        self.refresh()

    def _configure_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.focus_new_transaction)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.focus_search)
        QShortcut(QKeySequence(Qt.Key_Delete), self, activated=self.delete_selected_transaction)

    def focus_new_transaction(self) -> None:
        self.label_edit.setFocus()
        self.label_edit.selectAll()

    def focus_search(self) -> None:
        self.filter_search.setFocus()
        self.filter_search.selectAll()

    def load_categories(self) -> None:
        self.category_combo.clear()
        self.filter_category.clear()
        self.filter_category.addItem("Toutes", None)
        for cat in self.category_service.list_categories():
            self.category_combo.addItem(cat.name, cat.id)
            self.filter_category.addItem(cat.name, cat.id)

    def restore_filters(self) -> None:
        raw_value = self.settings_service.get_setting("transactions_filtres", "")
        if not raw_value:
            today = QDate.currentDate()
            first_day = QDate(today.year(), today.month(), 1)
            self.filter_start.setDate(first_day)
            self.filter_end.setDate(today)
            return
        try:
            data = json.loads(raw_value)
            self.filter_start.setDate(QDate.fromString(data["start_date"], "yyyy-MM-dd"))
            self.filter_end.setDate(QDate.fromString(data["end_date"], "yyyy-MM-dd"))
            index = self.filter_category.findData(data.get("category_id"))
            self.filter_category.setCurrentIndex(max(index, 0))
            self.filter_search.setText(data.get("search", ""))
        except (ValueError, KeyError, TypeError):
            today = QDate.currentDate()
            self.filter_start.setDate(QDate(today.year(), today.month(), 1))
            self.filter_end.setDate(today)

    def save_filters(self) -> None:
        payload = {
            "start_date": self.filter_start.date().toString("yyyy-MM-dd"),
            "end_date": self.filter_end.date().toString("yyyy-MM-dd"),
            "category_id": self.filter_category.currentData(),
            "search": self.filter_search.text().strip(),
        }
        self.settings_service.set_setting("transactions_filtres", json.dumps(payload, ensure_ascii=False))

    def reset_filters(self) -> None:
        today = QDate.currentDate()
        self.filter_start.setDate(QDate(today.year(), today.month(), 1))
        self.filter_end.setDate(today)
        self.filter_category.setCurrentIndex(0)
        self.filter_search.clear()
        self.refresh()

    def refresh(self) -> None:
        self.save_filters()
        transactions = self.tx_service.list_transactions(
            start_date=self.filter_start.date().toString("yyyy-MM-dd"),
            end_date=self.filter_end.date().toString("yyyy-MM-dd"),
            category_id=self.filter_category.currentData(),
            search=self.filter_search.text().strip() or None,
        )
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(transactions))
        for row_idx, tx in enumerate(transactions):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(tx.id or "")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(tx.date))
            self.table.setItem(row_idx, 2, QTableWidgetItem(tx.label))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{tx.amount:.2f}"))
            category_name = self.category_combo.itemText(self.category_combo.findData(tx.category_id))
            self.table.setItem(row_idx, 4, QTableWidgetItem(category_name))
            self.table.setItem(row_idx, 5, QTableWidgetItem(tx.payment_method))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(tx.counterparty_id or "")))
            self.table.setItem(row_idx, 7, QTableWidgetItem(tx.note))
        self.table.setSortingEnabled(True)

    def save_transaction(self) -> None:
        try:
            amount = Decimal(self.amount_edit.text().replace(",", "."))
        except InvalidOperation:
            QMessageBox.warning(self, "Montant invalide", "Le montant est obligatoire et doit être numérique.")
            self.amount_edit.setFocus()
            return
        if not self.label_edit.text().strip():
            QMessageBox.warning(self, "Libellé requis", "Le libellé est obligatoire.")
            self.label_edit.setFocus()
            return

        tx = Transaction(
            id=None,
            date=self.date_edit.date().toString("yyyy-MM-dd"),
            label=self.label_edit.text().strip(),
            amount=amount,
            category_id=self.category_combo.currentData(),
            counterparty_id=None,
            payment_method=self.payment_edit.text().strip(),
            note=self.note_edit.toPlainText().strip(),
            attachment=self.attachment_edit.text().strip() or None,
        )
        self.tx_service.create_transaction(tx)
        self.refresh()
        self.label_edit.clear()
        self.amount_edit.clear()
        self.payment_edit.clear()
        self.counterparty_edit.clear()
        self.note_edit.clear()
        self.attachment_edit.clear()
        self.label_edit.setFocus()

    def delete_selected_transaction(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        id_item = self.table.item(row, 0)
        if not id_item or not id_item.text().isdigit():
            return
        if (
            QMessageBox.question(
                self,
                "Confirmer la suppression",
                "Supprimer la transaction sélectionnée ?",
            )
            != QMessageBox.Yes
        ):
            return
        self.tx_service.delete_transaction(int(id_item.text()))
        self.refresh()

    def select_attachment(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier")
        if file_path:
            self.attachment_edit.setText(file_path)
