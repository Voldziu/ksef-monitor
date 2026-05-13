"""Manually fetch invoices from KSeF for a given date range."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from app.config import Settings
from app.ksef.service import KsefService
from app.notifications.factory import build_connectors
from app.runner import run_once
from app.storage.repository import Repository
from app.utils.date import _parse_dt, _today_midnight
from app.utils.logger import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch KSeF invoices for a date range")
    parser.add_argument(
        "--start-date",
        type=_parse_dt,
        default=_today_midnight(),
        help="Start date (ISO format). Defaults to today at midnight UTC.",
    )
    parser.add_argument(
        "--end-date",
        type=_parse_dt,
        default=datetime.now(UTC),
        help="End date (ISO format). Defaults to now (UTC).",
    )
    args = parser.parse_args()

    settings = Settings()
    setup_logging(settings)
    repo = Repository(settings.STORAGE_PATH)
    connectors = build_connectors(settings)
    ksef_service = KsefService(settings)

    print(
        f"Fetching invoices from {args.start_date.isoformat()} "
        f"to {args.end_date.isoformat()}",
    )

    result = run_once(
        ksef_service,
        repo,
        connectors,
        nip=settings.KSEF_NIP or "0000000000",
        since=args.start_date,
        to=args.end_date,
    )
    print(
        f"Wynik: new={result.new_count} "
        f"skipped={result.skipped_count} errors={result.errors}",
    )


if __name__ == "__main__":
    main()
