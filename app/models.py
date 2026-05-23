from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PaymentInfo:
    payment_due_date: str | None = None
    paid: bool | None = None
    payment_date: str | None = None
    paid_partially: bool | None = None
    paid_amount: float | None = None
    payment_form_code: str | None = None
    bank_account_number: str | None = None


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
    payment: PaymentInfo = field(default_factory=PaymentInfo)


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
