"""Per-exchange trading pause and go-live state (S16)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trendalgo.exchanges.registry import list_trading_exchanges


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


CONTROL_SCHEMA = """
CREATE TABLE IF NOT EXISTS exchange_trading_state (
    exchange_id TEXT PRIMARY KEY,
    paused INTEGER NOT NULL DEFAULT 0,
    go_live_approved INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""


class ExchangeControlStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(CONTROL_SCHEMA)
            self._seed(conn)

    def _seed(self, conn: sqlite3.Connection) -> None:
        for entry in list_trading_exchanges():
            row = conn.execute(
                "SELECT 1 FROM exchange_trading_state WHERE exchange_id = ?",
                (entry.id,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO exchange_trading_state (exchange_id, paused, go_live_approved, updated_at) "
                    "VALUES (?, 0, 0, ?)",
                    (entry.id, _utc_now()),
                )

    def set_paused(self, exchange_id: str, paused: bool) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE exchange_trading_state SET paused = ?, updated_at = ? WHERE exchange_id = ?",
                (int(paused), _utc_now(), exchange_id),
            )

    def approve_go_live(self, exchange_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE exchange_trading_state SET go_live_approved = 1, updated_at = ? WHERE exchange_id = ?",
                (_utc_now(), exchange_id),
            )

    def get(self, exchange_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM exchange_trading_state WHERE exchange_id = ?",
                (exchange_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "exchange_id": row["exchange_id"],
                "paused": bool(row["paused"]),
                "go_live_approved": bool(row["go_live_approved"]),
                "updated_at": row["updated_at"],
            }

    def list_status(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM exchange_trading_state ORDER BY exchange_id").fetchall()
            return [
                {
                    "exchange_id": r["exchange_id"],
                    "paused": bool(r["paused"]),
                    "go_live_approved": bool(r["go_live_approved"]),
                    "updated_at": r["updated_at"],
                }
                for r in rows
            ]

    def can_execute(self, exchange_id: str, *, dry_run: bool) -> tuple[bool, str]:
        row = self.get(exchange_id)
        if row is None:
            return False, "unknown_exchange"
        if row["paused"]:
            return False, "exchange_paused"
        if not dry_run and not row["go_live_approved"]:
            return False, "go_live_required"
        return True, "ok"
