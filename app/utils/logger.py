from __future__ import annotations

import logging
import logging.handlers

from pythonjsonlogger.jsonlogger import JsonFormatter

from app.config import Settings

_configured = False

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)s:%(lineno)d | %(message)s"


class NoTracebackFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        exc_info, exc_text = record.exc_info, record.exc_text
        record.exc_info = None
        record.exc_text = None
        try:
            return super().format(record)
        finally:
            record.exc_info = exc_info
            record.exc_text = exc_text


class NoTracebackJsonFormatter(JsonFormatter):
    def format(self, record: logging.LogRecord) -> str:
        exc_info, exc_text = record.exc_info, record.exc_text
        record.exc_info = None
        record.exc_text = None
        try:
            return super().format(record)
        finally:
            record.exc_info = exc_info
            record.exc_text = exc_text


def setup_logging(settings: Settings) -> None:
    global _configured
    if _configured:
        return
    _configured = True

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)
    app_logger.handlers.clear()
    app_logger.propagate = False

    if settings.LOG_TO_CONSOLE:
        if settings.LOG_FORMAT == "json":
            fmt = NoTracebackJsonFormatter(
                "%(timestamp)s %(level)s %(logger)s %(module)s %(funcName)s %(lineno)d %(message)s",
                rename_fields={
                    "asctime": "timestamp",
                    "levelname": "level",
                    "name": "logger",
                },
            )
        else:
            fmt = NoTracebackFormatter(_LOG_FORMAT)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(fmt)
        app_logger.addHandler(ch)

    if settings.LOG_TO_FILE:
        settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

        file_fmt = NoTracebackFormatter(_LOG_FORMAT)

        fh = logging.handlers.RotatingFileHandler(
            settings.LOG_DIR / settings.LOG_FILE_NAME,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setLevel(level)
        fh.setFormatter(file_fmt)
        app_logger.addHandler(fh)

        eh = logging.handlers.RotatingFileHandler(
            settings.LOG_DIR / "errors.log",
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        eh.setLevel(logging.ERROR)

        error_fmt = logging.Formatter(_LOG_FORMAT)
        eh.setFormatter(error_fmt)
        app_logger.addHandler(eh)

    for noisy in ("urllib3", "httpx", "httpcore", "smtplib", "ksef_client"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
