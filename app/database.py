"""SQLite decision memory (Lesson 10).

Prevents reprocessing the same Gmail message_id and stores an audit trail.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATABASE_PATH
from app.models import ClassificationResult, EmailMessage


SCHEMA = """
CREATE TABLE IF NOT EXISTS email_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    thread_id TEXT,
    sender TEXT,
    subject TEXT,
    category TEXT,
    importance TEXT,
    confidence REAL,
    reason TEXT,
    action TEXT,
    execution_note TEXT,
    created_at TEXT NOT NULL
);
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class DecisionStore:
    """Local SQLite store for classification/action history."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path or DATABASE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(SCHEMA)
            conn.commit()

    def has_message(self, message_id: str) -> bool:
        """Return True if this Gmail message was already processed."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM email_decisions WHERE message_id = ? LIMIT 1",
                (message_id,),
            ).fetchone()
        return row is not None

    def save_decision(
        self,
        email: EmailMessage,
        decision: ClassificationResult,
        *,
        execution_note: str = "",
        action: str | None = None,
    ) -> None:
        """Insert or update the audit row for a message."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO email_decisions (
                    message_id, thread_id, sender, subject,
                    category, importance, confidence, reason,
                    action, execution_note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    sender = excluded.sender,
                    subject = excluded.subject,
                    category = excluded.category,
                    importance = excluded.importance,
                    confidence = excluded.confidence,
                    reason = excluded.reason,
                    action = excluded.action,
                    execution_note = excluded.execution_note,
                    created_at = excluded.created_at
                """,
                (
                    email.message_id,
                    email.thread_id,
                    email.sender,
                    email.subject,
                    decision.category.value,
                    decision.importance.value,
                    decision.confidence,
                    decision.reason,
                    action or decision.action.value,
                    execution_note,
                    utc_now_iso(),
                ),
            )
            conn.commit()

    def get_decision(self, message_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM email_decisions WHERE message_id = ?",
                (message_id,),
            ).fetchone()

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM email_decisions").fetchone()
        return int(row["n"]) if row else 0
