"""Backtest library persistence (T32)."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


LIBRARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy TEXT NOT NULL,
    pair TEXT NOT NULL,
    tag TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class BacktestLibrary:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(LIBRARY_SCHEMA)

    def save(
        self,
        strategy: str,
        pair: str,
        payload: dict[str, Any],
        *,
        tag: str | None = None,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO backtest_runs (strategy, pair, tag, version, payload_json, created_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (strategy, pair, tag, json.dumps(payload), _utc_now()),
            )
            return int(cur.lastrowid)

    def clone(self, run_id: int, new_tag: str | None = None) -> int:
        row = self.get(run_id)
        if row is None:
            raise ValueError("run not found")
        return self.save(
            row["strategy"],
            row["pair"],
            row["payload"],
            tag=new_tag or f"clone-{run_id}",
        )

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, strategy, pair, tag, version, created_at FROM backtest_runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get(self, run_id: int) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, strategy, pair, tag, version, payload_json, created_at FROM backtest_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "id": int(row["id"]),
                "strategy": row["strategy"],
                "pair": row["pair"],
                "tag": row["tag"],
                "version": int(row["version"]),
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
