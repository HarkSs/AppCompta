"""Logging configuration helpers."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import LOG_FILE, ensure_directories


def setup_logging() -> None:
    """Configure logging for the application."""
    ensure_directories()
    handler = RotatingFileHandler(LOG_FILE, maxBytes=512_000, backupCount=3, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[handler])


__all__ = ["setup_logging"]
