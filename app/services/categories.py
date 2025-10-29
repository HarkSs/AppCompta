"""Service layer for categories."""
from __future__ import annotations

from typing import List

from app.db.database import Database
from app.models.entities import Category


class CategoryService:
    """Manage categories."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def list_categories(self) -> List[Category]:
        rows = self.db.query("SELECT id, name, type FROM categories ORDER BY name")
        return [Category(id=row["id"], name=row["name"], type=row["type"]) for row in rows]

    def create_category(self, name: str, cat_type: str) -> int:
        cur = self.db.execute(
            "INSERT INTO categories(name, type) VALUES(?, ?)",
            (name, cat_type),
        )
        return int(cur.lastrowid)

    def delete_category(self, category_id: int) -> None:
        self.db.execute("DELETE FROM categories WHERE id=?", (category_id,))


__all__ = ["CategoryService"]
