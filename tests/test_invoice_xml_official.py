from __future__ import annotations

from pathlib import Path

import pytest

from app.ksef.invoice_xml import parse_payment_info
from app.ksef.validation import validate_fa3_xml

FIXTURES = Path(__file__).parent / "fixtures"
OFFICIAL_EXAMPLES = sorted(FIXTURES.glob("*Przykład*.xml"))


def _ids(paths: list[Path]) -> list[str]:
    return [p.name for p in paths]


@pytest.mark.parametrize("path", OFFICIAL_EXAMPLES, ids=_ids(OFFICIAL_EXAMPLES))
def test_official_example_validates_against_xsd(path: Path):
    errors = validate_fa3_xml(path.read_bytes())
    assert errors == [], f"{path.name} failed XSD validation: {errors[:3]}"


@pytest.mark.parametrize("path", OFFICIAL_EXAMPLES, ids=_ids(OFFICIAL_EXAMPLES))
def test_parser_does_not_crash_on_official_example(path: Path):
    parse_payment_info(path.read_text(encoding="utf-8"))


def test_official_example_with_platnosc_extracts_fields():
    paid_examples = [
        p for p in OFFICIAL_EXAMPLES if b"<Platnosc>" in p.read_bytes()
    ]
    assert paid_examples, "expected at least one example with <Platnosc>"
    parsed = [parse_payment_info(p.read_text(encoding="utf-8")) for p in paid_examples]
    assert any(
        info.payment_due_date or info.paid or info.payment_form_code
        for info in parsed
    ), "expected at least one example to yield non-empty payment fields"
