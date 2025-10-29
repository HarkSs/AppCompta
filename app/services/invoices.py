"""Invoice service placeholder for v2."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List

from app.models.entities import Invoice


class InvoiceService:
    """Minimal placeholder for invoice management."""

    def list_invoices(self) -> List[Invoice]:
        # Will be implemented in v2.
        return []


__all__ = ["InvoiceService"]
