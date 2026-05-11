from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import Settings
from app.models import NotificationPayload
from app.notifications.base import NotificationConnector
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MailConnector(NotificationConnector):
    name = "mail"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, payload: NotificationPayload) -> None:
        recipients = self._settings.MAIL_TO
        if not recipients:
            logger.warning("No MAIL_TO recipients configured, skipping mail notification")
            return

        logger.info("Sending mail to=%s subject=%r", recipients, payload.subject)
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = payload.subject
            msg["From"] = self._settings.MAIL_FROM
            msg["To"] = ", ".join(recipients)

            msg.attach(MIMEText(payload.body_text, "plain", "utf-8"))
            if payload.body_html:
                msg.attach(MIMEText(payload.body_html, "html", "utf-8"))

            self._deliver(msg, recipients)
            logger.info("Mail sent successfully to %s", recipients)
        except smtplib.SMTPException as exc:
            logger.exception("SMTP error while sending mail: %s", exc)
            raise

    def health_check(self) -> bool:
        try:
            with self._smtp() as smtp:
                smtp.noop()
            return True
        except Exception as exc:
            logger.warning("Mail health check failed: %s", exc)
            return False

    def _smtp(self) -> smtplib.SMTP:
        s = self._settings
        smtp = smtplib.SMTP(s.MAIL_HOST, s.MAIL_PORT, timeout=10)
        if s.MAIL_USE_TLS:
            smtp.starttls()
        if s.MAIL_USER:
            smtp.login(s.MAIL_USER, s.MAIL_PASSWORD)
        return smtp

    def _deliver(self, msg: MIMEMultipart, recipients: list[str]) -> None:
        with self._smtp() as smtp:
            smtp.sendmail(self._settings.MAIL_FROM, recipients, msg.as_string())
