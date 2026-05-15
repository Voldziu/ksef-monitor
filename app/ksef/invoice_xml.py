from __future__ import annotations

from xml.etree import ElementTree as ET

from app.models import PaymentInfo
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _local(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _find_child(element: ET.Element, name: str) -> ET.Element | None:
    for child in element:
        if _local(child.tag) == name:
            return child
    return None


def _find_descendant(element: ET.Element, name: str) -> ET.Element | None:
    for descendant in element.iter():
        if _local(descendant.tag) == name:
            return descendant
    return None


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    text = element.text.strip()
    return text or None


def _parse_bool_flag(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true"}:
        return True
    if normalized in {"0", "false"}:
        return False
    return None


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def parse_payment_info(xml: str) -> PaymentInfo:
    """Extract Fa/Platnosc fields from an FA(2)/FA(3) KSeF invoice XML.

    Namespace-agnostic — matches by local element name so a single
    implementation covers FA(2) and FA(3) schemas.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        logger.warning("Failed to parse invoice XML: %s", exc)
        return PaymentInfo()

    fa = _find_descendant(root, "Fa")
    if fa is None:
        return PaymentInfo()
    platnosc = _find_child(fa, "Platnosc")
    if platnosc is None:
        return PaymentInfo()

    termin_platnosci = _find_child(platnosc, "TerminPlatnosci")
    payment_due_date: str | None = None
    if termin_platnosci is not None:
        payment_due_date = _text(_find_child(termin_platnosci, "Termin"))

    return PaymentInfo(
        payment_due_date=payment_due_date,
        paid=_parse_bool_flag(_text(_find_child(platnosc, "Zaplacono"))),
        payment_date=_text(_find_child(platnosc, "DataZaplaty")),
        paid_partially=_parse_bool_flag(
            _text(_find_child(platnosc, "ZaplaconoCzesciowo")),
        ),
        paid_amount=_parse_float(_text(_find_child(platnosc, "KwotaZaplacona"))),
        payment_form_code=_text(_find_child(platnosc, "FormaPlatnosci")),
    )
