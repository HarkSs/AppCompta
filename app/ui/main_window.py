"""Main window assembly."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMainWindow, QStackedWidget

from app.db.database import Database, bootstrap
from app.services.backups import BackupService
from app.services.categories import CategoryService
from app.services.reports import ReportService
from app.services.settings import SettingsService
from app.services.transactions import TransactionService
from app.ui.dashboard import DashboardView
from app.ui.invoices import InvoicesView
from app.ui.reports import ReportsView
from app.ui.settings import SettingsView
from app.ui.transactions import TransactionsView

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Top-level window with navigation."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MaCompta")
        self.resize(1024, 720)

        self.db = Database()
        bootstrap(self.db)

        self.settings_service = SettingsService(self.db)
        self.category_service = CategoryService(self.db)
        self.tx_service = TransactionService(self.db)
        self.report_service = ReportService(self.db)
        self.backup_service = BackupService(self.db)

        self.navigation = QListWidget()
        self.navigation.addItem(QListWidgetItem("Tableau de bord"))
        self.navigation.addItem(QListWidgetItem("Transactions"))
        self.navigation.addItem(QListWidgetItem("Factures"))
        self.navigation.addItem(QListWidgetItem("Rapports"))
        self.navigation.addItem(QListWidgetItem("Paramètres"))
        self.navigation.setCurrentRow(0)
        self.navigation.currentRowChanged.connect(self.change_page)

        self.stack = QStackedWidget()
        self.dashboard = DashboardView(self.report_service)
        self.transactions = TransactionsView(self.tx_service, self.category_service)
        self.invoices = InvoicesView()
        self.reports = ReportsView(self.report_service)
        self.settings = SettingsView(self.settings_service, self.backup_service)

        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.transactions)
        self.stack.addWidget(self.invoices)
        self.stack.addWidget(self.reports)
        self.stack.addWidget(self.settings)

        from PySide6.QtWidgets import QWidget, QHBoxLayout

        container = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(self.navigation)
        layout.addWidget(self.stack, stretch=1)
        container.setLayout(layout)
        self.setCentralWidget(container)

    def change_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.dashboard.refresh()
        elif index == 1:
            self.transactions.refresh()
        elif index == 3:
            self.reports.refresh()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        LOGGER.info("Fermeture application")
        self.db.close()
        super().closeEvent(event)
