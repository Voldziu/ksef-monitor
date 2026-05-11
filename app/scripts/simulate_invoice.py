"""Simulates invoice reception."""

from __future__ import annotations

import time

from app.config import Settings
from app.models import Invoice
from app.notifications.factory import build_connectors
from app.runner import run_once
from app.storage.repository import Repository
from app.utils.logger import setup_logging


class _FakeKsefService:
    def fetch_received_invoices(self, since):  # noqa: ANN001
        ref = f"TEST-{int(time.time())}"
        return [
            Invoice(
                ksef_reference_number=ref,
                seller_nip="1234567890",
                seller_name="Firma Testowa Sp. z o.o.",
                invoice_number="FV/TEST/2026/001",
                issue_date="2026-05-10",
                acquisition_date="2026-05-10",
                gross_amount=1230.00,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="1234563131",
                seller_name="Bynio Sp. z o.o.",
                invoice_number="FV/TEST/2026/001",
                issue_date="2026-05-10",
                acquisition_date="2026-05-10",
                gross_amount=1230.00,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="9876543210",
                seller_name="TechSolutions Polska S.A.",
                invoice_number="FS/2026/03/142",
                issue_date="2026-03-15",
                acquisition_date="2026-03-16",
                gross_amount=4920.75,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="5551237890",
                seller_name="Usługi Budowlane Kowalski",
                invoice_number="FV/2026/002",
                issue_date="2026-04-01",
                acquisition_date="2026-04-01",
                gross_amount=18450.00,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="7771112223",
                seller_name="Auto-Moto Import Sp. z o.o.",
                invoice_number="FAK/AUTO/2026/0055",
                issue_date="2026-01-20",
                acquisition_date="2026-01-22",
                gross_amount=61500.00,
                currency="EUR",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="3334445556",
                seller_name="Hurtownia Spożywcza Nowak",
                invoice_number="HN/2026/145",
                issue_date="2026-02-28",
                acquisition_date="2026-02-28",
                gross_amount=3276.90,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="6662227778",
                seller_name="Studio Graficzne Pixel Sp. z o.o.",
                invoice_number="SG/FV/2026/011",
                issue_date="2026-05-01",
                acquisition_date="2026-05-05",
                gross_amount=984.00,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="1112223334",
                seller_name="Kancelaria Prawna Wiśniewski i Wspólnicy",
                invoice_number="KPW/2026/033",
                issue_date="2026-04-15",
                acquisition_date="2026-04-15",
                gross_amount=7380.00,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="4445556667",
                seller_name="Drukarnia Expres S.A.",
                invoice_number="DE/FV/2026/0299",
                issue_date="2026-03-31",
                acquisition_date="2026-04-02",
                gross_amount=2214.00,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="8889990001",
                seller_name="Cloud Hosting Partners Sp. z o.o.",
                invoice_number="CHP/SUB/2026/04",
                issue_date="2026-04-30",
                acquisition_date="2026-04-30",
                gross_amount=492.00,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="2223334445",
                seller_name="Szkolenia i Rozwój Zawodowy Marek Zając",
                invoice_number="SRZ/2026/017",
                issue_date="2026-05-08",
                acquisition_date="2026-05-08",
                gross_amount=1845.00,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=ref,
                seller_nip="0009998887",
                seller_name="Logistyka Krajowa Sp. z o.o.",
                invoice_number="LK/TR/2026/1089",
                issue_date="2026-05-09",
                acquisition_date="2026-05-10",
                gross_amount=738.45,
                currency="PLN",
            ),
        ]


if __name__ == "__main__":
    settings = Settings()
    setup_logging(settings)
    repo = Repository(settings.STORAGE_PATH)
    connectors = build_connectors(settings)

    result = run_once(
        _FakeKsefService(),
        repo,
        connectors,
        nip=settings.KSEF_NIP or "0000000000",
    )
    print(
        f"Wynik: new={result.new_count} skipped={result.skipped_count} errors={result.errors}",
    )
