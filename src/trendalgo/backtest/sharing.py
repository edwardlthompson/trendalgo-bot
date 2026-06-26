"""Tokenized read-only backtest share links (T34)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SHARE_SCHEMA = """
CREATE TABLE IF NOT EXISTS backtest_shares (
    token TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT
);
"""


class BacktestShareStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SHARE_SCHEMA)

    def create_token(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True) + _utc_now()
        token = hashlib.sha256(raw.encode()).hexdigest()[:16]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO backtest_shares (token, payload_json, created_at, expires_at) VALUES (?,?,?,NULL)",
                (token, json.dumps(payload), _utc_now()),
            )
        return token

    def get(self, token: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT payload_json FROM backtest_shares WHERE token = ?",
                (token,),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row["payload_json"])
