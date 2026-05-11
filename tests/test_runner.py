from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.models import Invoice, MonitorResult
from app.runner import run_once


def _make_invoice(ref: str, number: str = "FV/1/2026") -> Invoice:
    return Invoice(
        ksef_reference_number=ref,
        seller_nip="1111111111",
        seller_name="Test Seller",
        invoice_number=number,
        issue_date="2026-05-07",
        acquisition_date="2026-05-07",
        gross_amount=123.00,
        currency="PLN",
    )


@pytest.fixture()
def repo(tmp_path: Path):
    from app.storage.repository import Repository
    return Repository(tmp_path / "test.db")


def test_new_invoices_are_notified_and_marked(repo):
    ksef_service = MagicMock()
    inv = _make_invoice("REF-001")
    ksef_service.fetch_received_invoices.return_value = [inv]

    connector = MagicMock()
    connector.name = "mock"

    result = run_once(ksef_service, repo, [connector], "1234567890")

    assert result.new_count == 1
    assert result.skipped_count == 0
    assert not result.errors
    connector.send.assert_called_once()
    assert repo.is_seen("REF-001")


def test_already_seen_invoice_is_skipped(repo):
    repo.mark_seen("REF-002")

    ksef_service = MagicMock()
    ksef_service.fetch_received_invoices.return_value = [_make_invoice("REF-002")]

    connector = MagicMock()
    connector.name = "mock"

    result = run_once(ksef_service, repo, [connector], "1234567890")

    assert result.new_count == 0
    assert result.skipped_count == 1
    connector.send.assert_not_called()


def test_connector_error_recorded_but_does_not_raise(repo):
    ksef_service = MagicMock()
    ksef_service.fetch_received_invoices.return_value = [_make_invoice("REF-003")]

    connector = MagicMock()
    connector.name = "failing"
    connector.send.side_effect = RuntimeError("SMTP down")

    result = run_once(ksef_service, repo, [connector], "1234567890")

    assert result.new_count == 1
    assert len(result.errors) == 1


def test_ksef_fetch_failure_returns_error_result(repo):
    ksef_service = MagicMock()
    ksef_service.fetch_received_invoices.side_effect = RuntimeError("timeout")

    result = run_once(ksef_service, repo, [], "1234567890")

    assert result.new_count == 0
    assert len(result.errors) == 1


def test_checkpoint_updated_after_run(repo):
    ksef_service = MagicMock()
    ksef_service.fetch_received_invoices.return_value = []

    assert repo.last_check_timestamp() is None
    run_once(ksef_service, repo, [], "1234567890")
    assert repo.last_check_timestamp() is not None
