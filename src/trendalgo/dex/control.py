"""Per-venue DEX trading pause and go-live state (S24)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.venues.registry import list_swap_venues


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


DEX_CONTROL_SCHEMA = """
CREATE TABLE IF NOT EXISTS dex_venue_trading_state (
    venue_id TEXT PRIMARY KEY,
    paused INTEGER NOT NULL DEFAULT 0,
    go_live_approved INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""


class DexVenueControlStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(DEX_CONTROL_SCHEMA)
            self._seed(conn)

    def _seed(self, conn: sqlite3.Connection) -> None:
        for entry in list_swap_venues():
            row = conn.execute(
                "SELECT 1 FROM dex_venue_trading_state WHERE venue_id = ?",
                (entry.id,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO dex_venue_trading_state (venue_id, paused, go_live_approved, updated_at) "
                    "VALUES (?, 0, 0, ?)",
                    (entry.id, _utc_now()),
                )

    def set_paused(self, venue_id: str, paused: bool) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE dex_venue_trading_state SET paused = ?, updated_at = ? WHERE venue_id = ?",
                (int(paused), _utc_now(), venue_id),
            )

    def approve_go_live(self, venue_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE dex_venue_trading_state SET go_live_approved = 1, updated_at = ? WHERE venue_id = ?",
                (_utc_now(), venue_id),
            )

    def get(self, venue_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM dex_venue_trading_state WHERE venue_id = ?",
                (venue_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "venue_id": row["venue_id"],
                "paused": bool(row["paused"]),
                "go_live_approved": bool(row["go_live_approved"]),
                "updated_at": row["updated_at"],
            }

    def list_status(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM dex_venue_trading_state ORDER BY venue_id"
            ).fetchall()
            return [
                {
                    "venue_id": r["venue_id"],
                    "paused": bool(r["paused"]),
                    "go_live_approved": bool(r["go_live_approved"]),
                    "updated_at": r["updated_at"],
                }
                for r in rows
            ]

    def can_execute(self, venue_id: str, *, live: bool) -> tuple[bool, str]:
        row = self.get(venue_id)
        if row is None:
            return False, "unknown_venue"
        if row["paused"]:
            return False, "venue_paused"
        if live and not row["go_live_approved"]:
            return False, "go_live_required"
        return True, "ok"
