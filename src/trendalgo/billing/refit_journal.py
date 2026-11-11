"""Re-fit events as billing journal rows (NOTIF-03)."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.db.rowid import require_row_id

_SCHEMA = """
CREATE TABLE IF NOT EXISTS billing_refit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    delivered INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class RefitBillingJournal:
    """Timestamp re-fit events for statement explanation, independent of delivery."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def append_event(
        self,
        *,
        event: str,
        payload: dict[str, Any],
        delivered: bool = False,
        created_at: str | None = None,
    ) -> int:
        ts = created_at or _utc_now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO billing_refit_events (event, payload_json, delivered, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event, json.dumps(payload, sort_keys=True), 1 if delivered else 0, ts),
            )
            return require_row_id(cur)

    def list_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, event, payload_json, delivered, created_at
                FROM billing_refit_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
