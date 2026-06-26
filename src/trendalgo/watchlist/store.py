"""Custom watchlists + price/P/L alerts (T8)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


WATCHLIST_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL UNIQUE,
    alert_price_pct REAL NOT NULL DEFAULT 0.05,
    alert_pl_usd REAL NOT NULL DEFAULT 50,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class WatchlistStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(WATCHLIST_SCHEMA)

    def add(self, pair: str, alert_price_pct: float = 0.05, alert_pl_usd: float = 50) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO watchlist_items (pair, alert_price_pct, alert_pl_usd, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (pair, alert_price_pct, alert_pl_usd, _utc_now()),
            )

    def list_items(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT pair, alert_price_pct, alert_pl_usd FROM watchlist_items").fetchall()
            return [dict(r) for r in rows]

    def log_alert(self, pair: str, message: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO watchlist_alerts (pair, message, created_at) VALUES (?, ?, ?)",
                (pair, message, _utc_now()),
            )

    def check_price_move(self, pair: str, move_pct: float) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT alert_price_pct FROM watchlist_items WHERE pair = ?", (pair,)).fetchone()
            if row is None:
                return None
            threshold = float(row["alert_price_pct"])
            if abs(move_pct) >= threshold:
                msg = f"{pair} moved {move_pct * 100:.1f}% (threshold {threshold * 100:.0f}%)"
                self.log_alert(pair, msg)
                return msg
            return None
