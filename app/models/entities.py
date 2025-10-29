"""Domain models for the application."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(slots=True)
class Category:
    id: int | None
    name: str
    type: str


@dataclass(slots=True)
class Counterparty:
    id: int | None
    name: str
    type: Optional[str]


@dataclass(slots=True)
class Transaction:
    id: int | None
    date: str
    label: str
    amount: Decimal
    category_id: int
    counterparty_id: Optional[int]
    payment_method: str
    note: str
    attachment: Optional[str]
    reconciled: bool = False
    external_ref: Optional[str] = None


@dataclass(slots=True)
class Invoice:
    id: int | None
    number: str
    date: str
    counterparty_id: int
    total_ht: Decimal
    total_tva: Decimal
    total_ttc: Decimal
    status: str
    pdf_path: Optional[str]
