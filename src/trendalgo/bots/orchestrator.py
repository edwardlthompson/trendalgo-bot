"""Multi-bot orchestrator (T10)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


BOT_SCHEMA = """
CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    pair TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    equity_usd REAL NOT NULL DEFAULT 1000,
    engine TEXT NOT NULL DEFAULT 'native',
    exchange TEXT NOT NULL DEFAULT 'kraken',
    created_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class BotRecord:
    id: int
    label: str
    strategy_id: str
    pair: str
    enabled: bool
    equity_usd: float
    engine: str
    exchange: str


class BotOrchestrator:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(BOT_SCHEMA)
            self._migrate(conn)
            count = conn.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
            if count == 0:
                conn.execute(
                    "INSERT INTO bots (label, strategy_id, pair, enabled, equity_usd, engine, exchange, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        "Bot-1",
                        "multi-tf-example",
                        "BTC/USD",
                        1,
                        1000,
                        "native",
                        "kraken",
                        _utc_now(),
                    ),
                )

    def _migrate(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(bots)").fetchall()}
        if "engine" not in cols:
            conn.execute("ALTER TABLE bots ADD COLUMN engine TEXT NOT NULL DEFAULT 'native'")
        if "exchange" not in cols:
            conn.execute("ALTER TABLE bots ADD COLUMN exchange TEXT NOT NULL DEFAULT 'kraken'")

    def list_bots(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM bots ORDER BY id").fetchall()
            return [
                {
                    "id": int(r["id"]),
                    "label": r["label"],
                    "strategy_id": r["strategy_id"],
                    "pair": r["pair"],
                    "enabled": bool(r["enabled"]),
                    "equity_usd": float(r["equity_usd"]),
                    "engine": r["engine"] if "engine" in r.keys() else "native",
                    "exchange": r["exchange"] if "exchange" in r.keys() else "kraken",
                }
                for r in rows
            ]

    def add_bot(
        self,
        label: str,
        strategy_id: str,
        pair: str,
        equity_usd: float = 1000,
        *,
        engine: str = "native",
        exchange: str = "kraken",
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO bots (label, strategy_id, pair, enabled, equity_usd, engine, exchange, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (label, strategy_id, pair, 1, equity_usd, engine, exchange, _utc_now()),
            )
            return int(cur.lastrowid)

    def set_enabled(self, bot_id: int, enabled: bool) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE bots SET enabled = ? WHERE id = ?", (int(enabled), bot_id))

    def count_enabled(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM bots WHERE enabled = 1").fetchone()
            return int(row[0])
