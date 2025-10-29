"""Database connection helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

from app.utils.paths import DATABASE_FILE, ensure_directories

SCHEMA_VERSION = 1


class Database:
    """Simple database wrapper."""

    def __init__(self, db_path: Path | None = None) -> None:
        ensure_directories()
        self.db_path = db_path or DATABASE_FILE
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self.connection.close()

    def execute(self, query: str, params: tuple | dict | None = None) -> sqlite3.Cursor:
        cur = self.connection.cursor()
        if params is None:
            cur.execute(query)
        else:
            cur.execute(query, params)
        self.connection.commit()
        return cur

    def executemany(self, query: str, params_seq: list[tuple]) -> sqlite3.Cursor:
        cur = self.connection.cursor()
        cur.executemany(query, params_seq)
        self.connection.commit()
        return cur

    def query(self, query: str, params: tuple | dict | None = None) -> list[sqlite3.Row]:
        cur = self.connection.cursor()
        if params is None:
            cur.execute(query)
        else:
            cur.execute(query, params)
        return cur.fetchall()


def bootstrap(db: Database) -> None:
    """Ensure database schema exists and migrations are applied."""
    create_schema(db)


def create_schema(db: Database) -> None:
    """Create initial schema if needed."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    current_version = get_schema_version(db)
    if current_version >= SCHEMA_VERSION:
        return
    db.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('schema_version', ?) ", (str(SCHEMA_VERSION),))
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            type TEXT CHECK(type IN ('recette','dépense'))
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS counterparties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            label TEXT,
            amount REAL,
            category_id INTEGER,
            counterparty_id INTEGER NULL,
            payment_method TEXT,
            note TEXT,
            attachment TEXT NULL,
            reconciled INTEGER DEFAULT 0,
            external_ref TEXT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id),
            FOREIGN KEY(counterparty_id) REFERENCES counterparties(id)
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tx_counterparty ON transactions(counterparty_id)")
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT UNIQUE,
            date TEXT,
            counterparty_id INTEGER,
            total_ht REAL,
            total_tva REAL,
            total_ttc REAL,
            status TEXT CHECK(status IN ('brouillon','émise','payée')),
            pdf_path TEXT NULL,
            FOREIGN KEY(counterparty_id) REFERENCES counterparties(id)
        )
        """
    )

    seed_categories(db)


def get_schema_version(db: Database) -> int:
    row = db.query("SELECT value FROM settings WHERE key='schema_version'")
    if not row:
        return 0
    return int(row[0][0])


def seed_categories(db: Database) -> None:
    existing = {row[0] for row in db.query("SELECT name FROM categories")}
    defaults = [
        ("Ventes", "recette"),
        ("Achats", "dépense"),
        ("Déplacements", "dépense"),
        ("Logiciels", "dépense"),
        ("Banque", "dépense"),
        ("Divers", "dépense"),
    ]
    to_insert = [item for item in defaults if item[0] not in existing]
    if to_insert:
        db.executemany("INSERT INTO categories(name, type) VALUES(?, ?)", to_insert)


__all__ = ["Database", "bootstrap", "create_schema", "seed_categories", "SCHEMA_VERSION"]
