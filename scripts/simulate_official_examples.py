"""Symuluje odbiór 25 oficjalnych przykładów FA(3) z KSeF."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from app.config import Settings
from app.ksef.invoice_xml import parse_payment_info
from app.ksef.validation import validate_fa3_xml
from app.models import Invoice, PaymentInfo
from app.notifications.factory import build_connectors
from app.runner import run_once
from app.storage.repository import Repository
from app.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
NS = "{http://crd.gov.pl/wzor/2025/06/25/13775/}"


def _find_text(root: ET.Element, path: str) -> str | None:
    ns_path = "/".join(f"{NS}{seg}" for seg in path.split("/"))
    el = root.find(f".//{ns_path}")
    return el.text.strip() if el is not None and el.text else None


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _build_invoice(xml_bytes: bytes, ref: str, not_skip: bool = False) -> Invoice:
    root = ET.fromstring(xml_bytes)
    payment = parse_payment_info(xml_bytes.decode("utf-8"))

    if not_skip:
        ref = f"ref_{datetime.now().isoformat()}"
    return Invoice(
        ksef_reference_number=ref,
        seller_nip=_find_text(root, "Podmiot1/DaneIdentyfikacyjne/NIP"),
        seller_name=_find_text(root, "Podmiot1/DaneIdentyfikacyjne/Nazwa"),
        invoice_number=_find_text(root, "Fa/P_2"),
        issue_date=_find_text(root, "Fa/P_1"),
        acquisition_date=_find_text(root, "Fa/P_1"),
        gross_amount=_to_float(_find_text(root, "Fa/P_15")),
        currency=_find_text(root, "Fa/KodWaluty"),
        payment=payment or PaymentInfo(),
    )


class _OfficialExamplesKsefService:
    def __init__(self, examples_dir: Path, not_skip: bool = False) -> None:
        self._paths = sorted(examples_dir.glob("*Przykład*.xml"))
        if not self._paths:
            raise FileNotFoundError(f"No FA(3) examples found in {examples_dir}")
        self._not_skip = not_skip

    def fetch_received_invoices(self, since=None, to=None):  # noqa: ANN001, ARG002
        invoices: list[Invoice] = []
        for path in self._paths:
            xml = path.read_bytes()
            errors = validate_fa3_xml(xml)
            if errors:
                logger.warning(
                    "%s failed XSD validation: %s",
                    path.name,
                    "; ".join(errors[:3]),
                )
            ref = f"SIM-{re.sub(r'[^A-Za-z0-9]+', '-', path.stem)}"
            invoices.append(_build_invoice(xml, ref, not_skip=self._not_skip))
        logger.info(
            "Simulated %d invoices from %s",
            len(invoices),
            self._paths[0].parent,
        )
        return invoices


if __name__ == "__main__":
    settings = Settings()
    setup_logging(settings)
    repo = Repository(settings.STORAGE_PATH)
    connectors = build_connectors(settings)

    service = _OfficialExamplesKsefService(FIXTURES_DIR, not_skip=True)
    result = run_once(
        service,
        repo,
        connectors,
        nip=settings.KSEF_NIP or "0000000000",
    )
    print(
        f"Wynik: new={result.new_count} skipped={result.skipped_count} "
        f"errors={result.errors}",
    )
