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
from ksef_client.services.workflows import AuthResult
from ksef_client.services.xades import XadesKeyPair

from app.config import Settings
from app.ksef.invoice_xml import parse_payment_info
from app.ksef.validation import validate_fa3_xml
from app.models import Invoice, PaymentInfo
from app.utils.date import _today_midnight
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


def _map_invoice(
    meta: InvoiceMetadata,
    payment: PaymentInfo | None = None,
) -> Invoice | None:
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
        payment=payment or PaymentInfo(),
    )


def _fetch_payment_info(
    client: KsefClient,
    ksef_number: str,
    access_token: str | None,
) -> PaymentInfo:
    if not access_token:
        return PaymentInfo()
    try:
        content = client.invoices.get_invoice(
            ksef_number,
            access_token=access_token,
        )
        errors = validate_fa3_xml(content.content)
        if errors:
            logger.warning(
                "Invoice XML failed FA(3) XSD validation (ksef_number=%s): %s",
                ksef_number,
                "; ".join(errors[:3]),
            )
        return parse_payment_info(content.content)
    except (KsefApiError, KsefHttpError) as exc:
        logger.warning(
            "Failed to fetch invoice XML for payment info (ksef_number=%s): %s",
            ksef_number,
            exc,
        )
        return PaymentInfo()


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
        method = self._settings.KSEF_AUTH_METHOD
        logger.info(
            "Authenticating with KSeF",
            extra={"env": self._settings.KSEF_ENV, "method": method},
        )
        self._access_token = None
        self._access_token_expires_at = None
        try:
            with KsefClient(self._options) as client:
                if method == "certificate":
                    result = self._authenticate_with_certificate(client)
                else:
                    result = self._authenticate_with_token(client)
                self._access_token = result.tokens.access_token.token
                self._access_token_expires_at = _parse_valid_until(
                    result.tokens.access_token.valid_until,
                )
            logger.info(
                "KSeF authentication successful (method=%s, valid until %s)",
                method,
                self._access_token_expires_at.astimezone().strftime(
                    "%Y-%m-%d %H:%M:%S",
                ),
            )
        except (KsefApiError, KsefHttpError) as exc:
            logger.exception(
                "KSeF authentication failed (method=%s): %s", method, exc,
            )
            raise

    def _authenticate_with_token(self, client: KsefClient) -> AuthResult:
        enc_cert = client.security.get_public_key_certificate(
            "KsefTokenEncryption",
        )
        return AuthCoordinator(client.auth).authenticate_with_ksef_token(
            token=self._settings.KSEF_TOKEN,
            public_certificate=enc_cert.certificate,
            public_key_id=enc_cert.public_key_id,
            context_identifier_type="NIP",
            context_identifier_value=self._settings.KSEF_NIP,
        )

    def _authenticate_with_certificate(self, client: KsefClient) -> AuthResult:
        key_pair = XadesKeyPair.from_pem_files(
            certificate_path=str(self._settings.KSEF_CERT_PATH),
            private_key_path=str(self._settings.KSEF_KEY_PATH),
            private_key_password=self._settings.KSEF_KEY_PASSWORD or None,
        )
        return AuthCoordinator(client.auth).authenticate_with_xades_key_pair(
            key_pair=key_pair,
            context_identifier_type="NIP",
            context_identifier_value=self._settings.KSEF_NIP,
            subject_identifier_type=self._settings.KSEF_CERT_SUBJECT_IDENTIFIER_TYPE,
        )

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
                    if not meta.ksef_number:
                        continue
                    payment = _fetch_payment_info(
                        client,
                        meta.ksef_number,
                        self._access_token,
                    )
                    inv = _map_invoice(meta, payment)
                    if inv:
                        invoices.append(inv)
                if not resp.has_more:
                    break
                page_offset += page_size
        return invoices

    def fetch_received_invoices(
        self,
        since: datetime | None = None,
        to: datetime | None = None,
    ) -> list[Invoice]:
        self._ensure_authenticated()

        if to is None:
            to = datetime.now(UTC)
        if since is None:
            since = _today_midnight()

        date_from = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        date_to = to.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(
            "Fetching received invoices [%s -> %s]",
            since.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            to.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
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
