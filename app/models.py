from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Invoice:
    ksef_reference_number: str
    seller_nip: str | None
    seller_name: str | None
    invoice_number: str | None
    issue_date: str | None
    acquisition_date: str | None
    gross_amount: float | None
    currency: str | None


@dataclass(frozen=True)
class NotificationPayload:
    subject: str
    body_text: str
    body_html: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MonitorResult:
    new_count: int
    skipped_count: int
    errors: list[str] = field(default_factory=list)
