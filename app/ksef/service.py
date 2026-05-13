from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ksef_client import KsefClient
from ksef_client.config import KsefClientOptions
from ksef_client.exceptions import KsefApiError, KsefHttpError
from ksef_client.models import (
    InvoiceMetadata,
    InvoiceQueryDateType,
    InvoiceQuerySubjectType,
)
from ksef_client.services import AuthCoordinator

from app.config import Settings
from app.models import Invoice
from app.utils.logger import get_logger

logger = get_logger(__name__)

_TOKEN_EXPIRY_MARGIN = timedelta(seconds=60)


def _parse_valid_until(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _map_invoice(meta: InvoiceMetadata) -> Invoice | None:
    if not meta.ksef_number:
        return None
    seller_nip: str | None = None
    seller_name: str | None = None
    if meta.seller:
        seller_nip = getattr(meta.seller, "identifier", None) or getattr(
            meta.seller,
            "nip",
            None,
        )
        seller_name = getattr(meta.seller, "full_name", None) or getattr(
            meta.seller,
            "name",
            None,
        )
    return Invoice(
        ksef_reference_number=meta.ksef_number,
        seller_nip=seller_nip,
        seller_name=seller_name,
        invoice_number=meta.invoice_number,
        issue_date=meta.issue_date,
        acquisition_date=meta.acquisition_date,
        gross_amount=meta.gross_amount,
        currency=meta.currency,
    )


class KsefService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._options = KsefClientOptions(base_url=settings.ksef_base_url())
        self._access_token: str | None = None
        self._access_token_expires_at: datetime | None = None

    def _is_token_valid(self) -> bool:
        if self._access_token is None:
            return False
        if self._access_token_expires_at is None:
            return True
        return datetime.now(UTC) + _TOKEN_EXPIRY_MARGIN < self._access_token_expires_at

    def _ensure_authenticated(self) -> None:
        if not self._is_token_valid():
            if self._access_token is not None:
                logger.info("KSeF access token expired, re-authenticating")
            self.authenticate()

    def authenticate(self) -> None:
        logger.info("Authenticating with KSeF", extra={"env": self._settings.KSEF_ENV})
        self._access_token = None
        self._access_token_expires_at = None
        try:
            with KsefClient(self._options) as client:
                enc_cert = client.security.get_public_key_certificate(
                    "KsefTokenEncryption",
                )
                result = AuthCoordinator(client.auth).authenticate_with_ksef_token(
                    token=self._settings.KSEF_TOKEN,
                    public_certificate=enc_cert.certificate,
                    public_key_id=enc_cert.public_key_id,
                    context_identifier_type="NIP",
                    context_identifier_value=self._settings.KSEF_NIP,
                )
                self._access_token = result.tokens.access_token.token
                self._access_token_expires_at = _parse_valid_until(
                    result.tokens.access_token.valid_until,
                )
            logger.info(
                "KSeF authentication successful (token valid until %s)",
                self._access_token_expires_at.astimezone().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            )
        except (KsefApiError, KsefHttpError) as exc:
            logger.exception("KSeF authentication failed: %s", exc)
            raise

    def _query_invoices(self, date_from: str, date_to: str) -> list[Invoice]:
        invoices: list[Invoice] = []
        with KsefClient(self._options, access_token=self._access_token) as client:
            page_offset = 0
            page_size = 100
            while True:
                resp = client.invoices.query_invoice_metadata_by_date_range(
                    subject_type=InvoiceQuerySubjectType.SUBJECT2,
                    date_type=InvoiceQueryDateType.INVOICING,
                    date_from=date_from,
                    date_to=date_to,
                    access_token=self._access_token,
                    page_size=page_size,
                    page_offset=page_offset,
                )
                for meta in resp.invoices:
                    inv = _map_invoice(meta)
                    if inv:
                        invoices.append(inv)
                if not resp.has_more:
                    break
                page_offset += page_size
        return invoices

    def fetch_received_invoices(self, since: datetime | None = None) -> list[Invoice]:
        self._ensure_authenticated()

        now = datetime.now(UTC)
        if since is None:
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)

        date_from = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        date_to = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(
            "Fetching received invoices [%s -> %s]",
            since.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            now.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        )

        try:
            invoices = self._query_invoices(date_from, date_to)
        except KsefHttpError as exc:
            if getattr(exc, "status_code", None) != 401:
                raise
            logger.warning(
                "KSeF returned 401, invalidating token and retrying once",
            )
            self._access_token = None
            self._access_token_expires_at = None
            self._ensure_authenticated()
            invoices = self._query_invoices(date_from, date_to)

        logger.info("Fetched %d invoices from KSeF", len(invoices))
        return invoices
