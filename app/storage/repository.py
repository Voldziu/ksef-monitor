from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


class Repository:
    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_invoices (
                    ksef_reference_number TEXT PRIMARY KEY,
                    seen_at               TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id        TEXT PRIMARY KEY,
                    last_seen TEXT NOT NULL
                )
                """
            )
            conn.commit()
        logger.debug("Database initialised at %s", self._path)

    def is_seen(self, ref: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM seen_invoices WHERE ksef_reference_number = ?", (ref,)
            ).fetchone()
        return row is not None

    def mark_seen(self, ref: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO seen_invoices (ksef_reference_number, seen_at) VALUES (?, ?)",
                (ref, now),
            )
            conn.commit()
        logger.debug("Marked as seen: %s", ref)

    def last_check_timestamp(self) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_seen FROM checkpoints WHERE id = 'default'"
            ).fetchone()
        if row is None:
            return None
        try:
            return datetime.fromisoformat(row[0])
        except ValueError:
            logger.warning("Could not parse stored checkpoint timestamp: %s", row[0])
            return None

    def save_check_timestamp(self, ts: datetime) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (id, last_seen) VALUES ('default', ?)",
                (ts.isoformat(),),
            )
            conn.commit()
