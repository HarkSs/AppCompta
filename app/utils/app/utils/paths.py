"""Utilities for managing application paths."""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "MaCompta"
DOCUMENTS_DIR = Path.home() / "Documents" / APP_NAME
BACKUP_DIR = DOCUMENTS_DIR / "backups"
DATABASE_FILE = DOCUMENTS_DIR / "donnees.db"
LOG_FILE = DOCUMENTS_DIR / "logs" / "app.log"


def ensure_directories() -> None:
    """Create required directories for the application."""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    assets_target = DOCUMENTS_DIR / "assets"
    assets_target.mkdir(exist_ok=True)


__all__ = [
    "APP_NAME",
    "DOCUMENTS_DIR",
    "BACKUP_DIR",
    "DATABASE_FILE",
    "LOG_FILE",
    "ensure_directories",
]
