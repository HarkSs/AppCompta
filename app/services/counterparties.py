"""Service layer for counterparties."""
from __future__ import annotations

from typing import List

from app.db.database import Database
from app.models.entities import Counterparty


class CounterpartyService:
    """Manage counterparties."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def list_counterparties(self) -> List[Counterparty]:
        rows = self.db.query("SELECT id, name, type FROM counterparties ORDER BY name")
        return [Counterparty(id=row["id"], name=row["name"], type=row["type"]) for row in rows]

    def upsert(self, name: str, cp_type: str | None = None) -> int:
        rows = self.db.query("SELECT id FROM counterparties WHERE name=?", (name,))
        if rows:
            cp_id = rows[0]["id"]
            self.db.execute("UPDATE counterparties SET type=? WHERE id=?", (cp_type, cp_id))
            return int(cp_id)
        cur = self.db.execute("INSERT INTO counterparties(name, type) VALUES(?, ?)", (name, cp_type))
        return int(cur.lastrowid)


__all__ = ["CounterpartyService"]
