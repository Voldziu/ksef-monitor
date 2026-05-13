from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import NotificationPayload


class ConnectorException(Exception): ...


class NotificationConnector(ABC):
    name: str

    @abstractmethod
    def send(self, payload: NotificationPayload) -> None: ...

    @abstractmethod
    def health_check(self) -> bool: ...
