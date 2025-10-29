"""Service layer for application settings."""
from __future__ import annotations

import json
from typing import Any, Dict

from app.db.database import Database

DEFAULT_SETTINGS: Dict[str, Any] = {
    "devise": "€",
    "regime": "auto-entrepreneur",
    "seuil_tva": "36500",
    "tolerance_rapprochement": "0.50",
    "dossier_backups": "",
}


class SettingsService:
    """Manage settings stored in the database."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_setting(self, key: str, default: str | None = None) -> str:
        rows = self.db.query("SELECT value FROM settings WHERE key=?", (key,))
        if rows:
            return rows[0]["value"]
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key]
        if default is not None:
            return default
        raise KeyError(key)

    def set_setting(self, key: str, value: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, value))

    def export_settings(self) -> Dict[str, Any]:
        rows = self.db.query("SELECT key, value FROM settings")
        data = {row["key"]: row["value"] for row in rows}
        for key, value in DEFAULT_SETTINGS.items():
            data.setdefault(key, value)
        return data

    def import_settings(self, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            self.set_setting(key, str(value))


__all__ = ["SettingsService", "DEFAULT_SETTINGS"]
