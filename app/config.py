from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # KSeF
    KSEF_ENV: Literal["test", "demo", "prod"] = "test"
    KSEF_NIP: str = ""
    KSEF_AUTH_METHOD: Literal["token", "certificate"] = "token"
    KSEF_TOKEN: str = ""
    KSEF_CERT_PATH: Path | None = None
    KSEF_KEY_PATH: Path | None = None
    KSEF_KEY_PASSWORD: str = ""
    KSEF_CERT_SUBJECT_IDENTIFIER_TYPE: str = "certificateSubject"
    CHECK_INTERVAL_MINUTES: int = 15
    KSEF_FETCH_DELAY_SECONDS: float = 0.5
    KSEF_FETCH_RETRY_COUNT: int = 3

    # Notifications
    NOTIFICATION_CHANNELS: list[str] = ["mail"]

    # Mail
    MAIL_HOST: str = "localhost"
    MAIL_PORT: int = 587
    MAIL_USER: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_TO: list[str] = []
    MAIL_USE_TLS: bool = True

    # Storage
    STORAGE_PATH: Path = Path("data/invoices.db")

    # Metrics
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 8000

    # Logger
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = Path("logs")
    LOG_FILE_NAME: str = "app.log"
    LOG_FORMAT: Literal["text", "json"] = "text"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5
    LOG_TO_CONSOLE: bool = True
    LOG_TO_FILE: bool = True

    @field_validator("KSEF_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        if v not in ("test", "demo", "prod"):
            raise ValueError("KSEF_ENV must be one of: test, demo, prod")
        return v

    @model_validator(mode="after")
    def validate_auth_method(self) -> Settings:
        if not self.KSEF_NIP:
            raise ValueError("KSEF_NIP is required")
        if self.KSEF_AUTH_METHOD == "token":
            if not self.KSEF_TOKEN:
                raise ValueError(
                    "KSEF_TOKEN is required when KSEF_AUTH_METHOD=token",
                )
        else:
            if self.KSEF_CERT_PATH is None or self.KSEF_KEY_PATH is None:
                raise ValueError(
                    "KSEF_CERT_PATH and KSEF_KEY_PATH are required when "
                    "KSEF_AUTH_METHOD=certificate",
                )
            if not self.KSEF_CERT_PATH.exists():
                raise ValueError(
                    f"KSEF_CERT_PATH does not exist: {self.KSEF_CERT_PATH}",
                )
            if not self.KSEF_KEY_PATH.exists():
                raise ValueError(
                    f"KSEF_KEY_PATH does not exist: {self.KSEF_KEY_PATH}",
                )
        return self

    def ksef_base_url(self) -> str:
        urls = {
            "test": "https://api-test.ksef.mf.gov.pl",
            "demo": "https://api-demo.ksef.mf.gov.pl",
            "prod": "https://api.ksef.mf.gov.pl",
        }
        return urls[self.KSEF_ENV]
