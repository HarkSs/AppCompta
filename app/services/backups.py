"""Backup and restore services."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from app.db.database import Database
from app.services.categories import CategoryService
from app.services.settings import SettingsService
from app.utils.paths import BACKUP_DIR, DATABASE_FILE, ensure_directories


class BackupService:
    """Handle backup and restore operations."""

    def __init__(self, db: Database) -> None:
        self.db = db
        ensure_directories()

    def auto_backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        target = BACKUP_DIR / f"backup-{timestamp}.zip"
        self.create_backup(target)
        return target

    def create_backup(self, path: Path) -> None:
        temp_dir = BACKUP_DIR / "temp"
        temp_dir.mkdir(exist_ok=True)
        shutil.copy(DATABASE_FILE, temp_dir / DATABASE_FILE.name)
        settings = SettingsService(self.db).export_settings()
        categories = CategoryService(self.db).list_categories()
        payload = {
            "settings": settings,
            "categories": [cat.__dict__ for cat in categories],
        }
        with (temp_dir / "metadata.json").open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        shutil.make_archive(path.with_suffix(""), "zip", temp_dir)
        shutil.rmtree(temp_dir)

    def restore_backup(self, archive: Path) -> None:
        temp_dir = BACKUP_DIR / "restore"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        shutil.unpack_archive(str(archive), temp_dir)
        shutil.copy(temp_dir / DATABASE_FILE.name, DATABASE_FILE)
        with (temp_dir / "metadata.json").open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        settings = SettingsService(self.db)
        for key, value in data.get("settings", {}).items():
            settings.set_setting(key, str(value))
        shutil.rmtree(temp_dir)


__all__ = ["BackupService"]
