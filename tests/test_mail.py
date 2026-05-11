from __future__ import annotations

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.models import NotificationPayload
from app.notifications.mail import MailConnector


def _settings(recipients: list[str] | None = None):
    s = MagicMock()
    s.MAIL_HOST = "localhost"
    s.MAIL_PORT = 1025
    s.MAIL_USE_TLS = False
    s.MAIL_USER = ""
    s.MAIL_PASSWORD = ""
    s.MAIL_FROM = "monitor@test.local"
    s.MAIL_TO = recipients or ["recipient@test.local"]
    return s


def _payload() -> NotificationPayload:
    return NotificationPayload(
        subject="Test: 2 new invoices",
        body_text="Invoice 1\nInvoice 2",
        body_html="<p>Invoice 1</p><p>Invoice 2</p>",
    )


def test_send_calls_smtp(tmp_path):
    connector = MailConnector(_settings())
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch.object(connector, "_smtp", return_value=mock_smtp):
        connector.send(_payload())

    mock_smtp.sendmail.assert_called_once()
    args = mock_smtp.sendmail.call_args[0]
    assert args[0] == "monitor@test.local"
    assert args[1] == ["recipient@test.local"]


def test_send_skips_when_no_recipients():
    connector = MailConnector(_settings(recipients=[]))
    mock_smtp = MagicMock()
    with patch.object(connector, "_smtp", return_value=mock_smtp):
        connector.send(_payload())
    mock_smtp.sendmail.assert_not_called()


def test_send_raises_on_smtp_error():
    connector = MailConnector(_settings())
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp.sendmail.side_effect = smtplib.SMTPException("connection refused")

    with patch.object(connector, "_smtp", return_value=mock_smtp):
        with pytest.raises(smtplib.SMTPException):
            connector.send(_payload())


def test_health_check_returns_true_on_success():
    connector = MailConnector(_settings())
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch.object(connector, "_smtp", return_value=mock_smtp):
        assert connector.health_check() is True


def test_health_check_returns_false_on_failure():
    connector = MailConnector(_settings())
    with patch.object(connector, "_smtp", side_effect=ConnectionRefusedError):
        assert connector.health_check() is False
