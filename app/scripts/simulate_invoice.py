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
                ksef_reference_number=f"TEST-{int(time.time())}",
                seller_nip="1234567890",
                seller_name="BYNIODENT Sp. z o.o.",
                invoice_number="FV/TEST/2026/001",
                issue_date="2026-05-10",
                acquisition_date="2026-05-10",
                gross_amount=1230.00,
                currency="PLN",
            ),
            Invoice(
                ksef_reference_number=f"TEST-{int(time.time() - 2)}",
                seller_nip="1234567890",
                seller_name="BYNIODENT Sp. z o.o.",
                invoice_number="FV/TEST/2026/002",
                issue_date="2026-05-11",
                acquisition_date="2026-05-11",
                gross_amount=1230.00,
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
