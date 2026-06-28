"""SQLite trade journal + fee ledger idempotency (M2 seed, R-014)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class TradeRecord:
    pair: str
    side: str
    stake_usd: float
    pnl_usd: float
    signal_source: str
    rationale: str
    exchange_trade_id: str
    exchange: str = ""
    bot_id: int | None = None


class TradeJournal:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _migrate(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(trades)").fetchall()}
        if "exchange" not in cols:
            conn.execute("ALTER TABLE trades ADD COLUMN exchange TEXT NOT NULL DEFAULT ''")
        if "bot_id" not in cols:
            conn.execute("ALTER TABLE trades ADD COLUMN bot_id INTEGER")

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair TEXT NOT NULL,
                    side TEXT NOT NULL,
                    stake_usd REAL NOT NULL,
                    pnl_usd REAL NOT NULL,
                    signal_source TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    exchange_trade_id TEXT NOT NULL UNIQUE,
                    exchange TEXT NOT NULL DEFAULT '',
                    bot_id INTEGER,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS fee_ledger_hooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (trade_id) REFERENCES trades(id)
                );
                """
            )
            self._migrate(conn)

    def append_trade(self, record: TradeRecord) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO trades (pair, side, stake_usd, pnl_usd, signal_source,
                    rationale, exchange_trade_id, exchange, bot_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.pair,
                    record.side,
                    record.stake_usd,
                    record.pnl_usd,
                    record.signal_source,
                    record.rationale,
                    record.exchange_trade_id,
                    record.exchange,
                    record.bot_id,
                    _utc_now(),
                ),
            )
            return int(cur.lastrowid)

    def record_fee_hook(
        self,
        trade_id: int,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> bool:
        """Return True if recorded; False if duplicate idempotency_key (R-014)."""
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO fee_ledger_hooks (trade_id, idempotency_key, payload_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (trade_id, idempotency_key, json.dumps(payload), _utc_now()),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def fee_hook_exists(self, idempotency_key: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM fee_ledger_hooks WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            return row is not None

    def count_trades(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM trades").fetchone()
            return int(row["c"]) if row else 0

    def list_trades(self, limit: int = 500) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT pair, side, stake_usd, pnl_usd, signal_source, rationale, "
                "exchange_trade_id, exchange, bot_id, created_at "
                "FROM trades ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_trades_for_bot(self, bot_id: int, limit: int = 500) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT pair, side, stake_usd, pnl_usd, signal_source, rationale, "
                "exchange_trade_id, exchange, bot_id, created_at "
                "FROM trades WHERE bot_id = ? ORDER BY id ASC LIMIT ?",
                (bot_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def pnl_for_bot(self, bot_id: int) -> dict[str, float | int]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl_usd), 0) AS pnl_usd, COUNT(*) AS trade_count "
                "FROM trades WHERE bot_id = ?",
                (bot_id,),
            ).fetchone()
        return {
            "pnl_usd": float(row["pnl_usd"]) if row else 0.0,
            "trade_count": int(row["trade_count"]) if row else 0,
        }
