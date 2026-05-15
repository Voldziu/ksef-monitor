from __future__ import annotations

from pathlib import Path

import pytest

from app.ksef.invoice_xml import parse_payment_info
from app.models import PaymentInfo

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_fa3_partial_payment():
    result = parse_payment_info(_load("invoice_fa3_partial.xml"))
    assert result == PaymentInfo(
        payment_due_date="2026-05-24",
        paid_partially=True,
        paid_amount=500.0,
        payment_form_code="6",
    )


@pytest.mark.parametrize("xml", ["", "<not-xml", "<Faktura><Fa></Fa>"])
def test_malformed_xml_returns_empty(xml: str):
    assert parse_payment_info(xml) == PaymentInfo()
