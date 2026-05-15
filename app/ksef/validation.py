from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from lxml import etree

_SCHEMAS_DIR = Path(__file__).parent / "schemas"
_FA_3_XSD = _SCHEMAS_DIR / "FA_3.xsd"


class InvoiceValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors) if errors else "invalid invoice XML")
        self.errors = errors


@lru_cache(maxsize=1)
def _fa3_schema() -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(_FA_3_XSD)))


def validate_fa3_xml(xml: str | bytes) -> list[str]:
    payload = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        doc = etree.fromstring(payload)
    except etree.XMLSyntaxError as exc:
        return [f"malformed XML: {exc}"]
    schema = _fa3_schema()
    if schema.validate(doc):
        return []
    return [f"{e.line}:{e.column} {e.message}" for e in schema.error_log]


def assert_valid_fa3(xml: str | bytes) -> None:
    errors = validate_fa3_xml(xml)
    if errors:
        raise InvoiceValidationError(errors)
