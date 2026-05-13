from __future__ import annotations

import time
from datetime import UTC, datetime

from ksef_client.exceptions import KsefApiError, KsefHttpError, KsefRateLimitError

from app import metrics
from app.ksef.service import KsefService
from app.models import Invoice, MonitorResult, NotificationPayload
from app.notifications.base import ConnectorException, NotificationConnector
from app.storage.repository import Repository
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _build_payload(invoices: list[Invoice], nip: str) -> NotificationPayload:
    count = len(invoices)
    subject = f"Nowe faktury w KSeF: {count}"

    lines = [f"Wykryto {count} nowych faktur w KSeF dla NIP {nip}:", ""]
    for inv in invoices:
        amount = f"{inv.gross_amount:.2f} {inv.currency}" if inv.gross_amount else "—"
        lines.append(
            f"  • {inv.ksef_reference_number} | {inv.invoice_number or '—'} | "
            f"{inv.seller_name or inv.seller_nip or '—'} | {amount} | {inv.issue_date or '—'}",
        )

    body_text = "\n".join(lines)

    html_rows = "".join(
        f"<tr><td>{inv.ksef_reference_number}</td><td>{inv.invoice_number or '—'}</td>"
        f"<td>{inv.seller_name or inv.seller_nip or '—'}</td>"
        f"<td>{f'{inv.gross_amount:.2f} {inv.currency}' if inv.gross_amount else '—'}</td>"
        f"<td>{inv.issue_date or '—'}</td></tr>"
        for inv in invoices
    )
    body_html = (
        "<p> Fajne zrobiłem? Narazie testowo :D</p>"
        f"<p>Wykryto {count} nowych faktur w KSeF dla NIP {nip}:</p>"
        "<table border='1' cellpadding='4' cellspacing='0'>"
        "<tr><th>Nr KSeF</th><th>Nr faktury</th><th>Sprzedawca</th><th>Kwota brutto</th><th>Data wystawienia</th></tr>"
        f"{html_rows}</table>"
    )

    return NotificationPayload(
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        metadata={"nip": nip, "count": count},
    )


def run_once(
    ksef_service: KsefService,
    repo: Repository,
    connectors: list[NotificationConnector],
    nip: str,
) -> MonitorResult:
    errors: list[str] = []
    new_invoices: list[Invoice] = []
    skipped = 0
    _t0 = time.perf_counter()

    since = repo.last_check_timestamp()
    check_start = datetime.now(UTC)

    try:
        all_invoices = ksef_service.fetch_received_invoices(since=since)
    except (KsefRateLimitError, KsefApiError, KsefHttpError, Exception) as exc:
        if isinstance(exc, KsefRateLimitError):
            logger.exception(
                "KSeF rate limit exceeded (429), retry_after=%s seconds",
                exc.retry_after,
            )
        elif isinstance(exc, KsefApiError):
            logger.exception("KSeF API error: %s", exc)
        elif isinstance(exc, KsefHttpError):
            logger.exception("KSeF HTTP error: %s", exc)
        else:
            logger.exception("Failed to fetch invoices from KSeF: %s", exc)

        result = MonitorResult(new_count=0, skipped_count=0, errors=[str(exc)])
        metrics.record_cycle(result, time.perf_counter() - _t0)
        return result

    for inv in all_invoices:
        if repo.is_seen(inv.ksef_reference_number):
            skipped += 1
        else:
            new_invoices.append(inv)

    if new_invoices:
        payload = _build_payload(new_invoices, nip)
        for connector in connectors:
            try:
                connector.send(payload)
            except ConnectorException as exc:
                logger.exception("Connector %r failed: %s", connector.name, exc)
            except Exception as exc:
                logger.exception(
                    "Unexpected error in connector %r: %s",
                    connector.name,
                    exc,
                )
            logger.info("Connector %r done", connector.name)

        for inv in new_invoices:
            repo.mark_seen(inv.ksef_reference_number)

    repo.save_check_timestamp(check_start)

    result = MonitorResult(
        new_count=len(new_invoices),
        skipped_count=skipped,
        errors=errors,
    )
    metrics.record_cycle(result, time.perf_counter() - _t0)
    logger.info(
        "Cycle done: new=%d skipped=%d errors=%d",
        result.new_count,
        result.skipped_count,
        len(result.errors),
    )
    return result
