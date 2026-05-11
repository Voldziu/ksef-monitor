from __future__ import annotations

from app.config import Settings
from app.notifications.base import NotificationConnector
from app.utils.logger import get_logger

logger = get_logger(__name__)


def build_connectors(settings: Settings) -> list[NotificationConnector]:
    connectors: list[NotificationConnector] = []
    for channel in settings.NOTIFICATION_CHANNELS:
        if channel == "mail":
            from app.notifications.mail import MailConnector
            connectors.append(MailConnector(settings))
        else:
            logger.warning("Unknown notification channel %r — skipping", channel)
    logger.info("Loaded notification connectors: %s", [c.name for c in connectors])
    return connectors
