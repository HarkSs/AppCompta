"""Settings screen."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.backups import BackupService
from app.services.settings import SettingsService
from app.utils.paths import BACKUP_DIR


class SettingsView(QWidget):
    """Allow editing settings and managing backups."""

    def __init__(self, settings: SettingsService, backups: BackupService) -> None:
        super().__init__()
        self.settings = settings
        self.backups = backups

        self.devise_edit = QLineEdit(self.settings.get_setting("devise"))
        self.regime_edit = QLineEdit(self.settings.get_setting("regime"))
        self.seuil_edit = QLineEdit(self.settings.get_setting("seuil_tva"))
        self.tolerance_edit = QLineEdit(self.settings.get_setting("tolerance_rapprochement"))
        self.backup_dir_edit = QLineEdit(self.settings.get_setting("dossier_backups", str(BACKUP_DIR)))

        choose_btn = QPushButton("Choisir…")
        choose_btn.clicked.connect(self.choose_backup_dir)
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self.save_settings)
        backup_btn = QPushButton("Backup immédiat")
        backup_btn.clicked.connect(self.create_backup)

        form = QFormLayout()
        form.addRow("Devise", self.devise_edit)
        form.addRow("Régime", self.regime_edit)
        form.addRow("Seuil TVA", self.seuil_edit)
        form.addRow("Tolérance rapprochement", self.tolerance_edit)
        form.addRow("Dossier backups", self.backup_dir_edit)
        form.addRow("", choose_btn)
        form.addRow(save_btn)
        form.addRow(backup_btn)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Paramètres"))
        layout.addLayout(form)
        layout.addStretch()
        self.setLayout(layout)

    def choose_backup_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choisir le dossier de backups")
        if directory:
            self.backup_dir_edit.setText(directory)

    def save_settings(self) -> None:
        self.settings.set_setting("devise", self.devise_edit.text())
        self.settings.set_setting("regime", self.regime_edit.text())
        self.settings.set_setting("seuil_tva", self.seuil_edit.text())
        self.settings.set_setting("tolerance_rapprochement", self.tolerance_edit.text())
        self.settings.set_setting("dossier_backups", self.backup_dir_edit.text())

    def create_backup(self) -> None:
        self.backups.create_backup(BACKUP_DIR / "manuel.zip")
