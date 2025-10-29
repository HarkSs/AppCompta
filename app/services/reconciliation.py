"""Reconciliation helpers."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable, List, Tuple

from app.models.entities import Transaction


def reconcile(transactions: List[Transaction], tolerance: Decimal) -> List[int]:
    """Return IDs of transactions considered reconciled based on amount tolerance."""
    reconciled_ids: List[int] = []
    seen: set[Decimal] = set()
    for tx in transactions:
        key = tx.amount.quantize(Decimal("0.01"))
        for existing in list(seen):
            if abs(existing - key) <= tolerance:
                if tx.id is not None:
                    reconciled_ids.append(tx.id)
                break
        else:
            if tx.id is not None:
                seen.add(key)
    return reconciled_ids


__all__ = ["reconcile"]
