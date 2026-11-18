"""SQLite trade journal + fee ledger idempotency (M2 seed, R-014, BILL-04)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.db.rowid import require_row_id

_GENESIS = "0" * 64


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _canon_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    for key in ("stake_usd", "pnl_usd"):
        if key in out and out[key] is not None:
            out[key] = float(out[key])
    return out


def _entry_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    body = json.dumps(
        {"prev": prev_hash, **_canon_payload(payload)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest()


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
        if "entry_hash" not in cols:
            conn.execute("ALTER TABLE trades ADD COLUMN entry_hash TEXT NOT NULL DEFAULT ''")
        if "prev_hash" not in cols:
            conn.execute("ALTER TABLE trades ADD COLUMN prev_hash TEXT NOT NULL DEFAULT ''")
        if "fill_ts" not in cols:
            conn.execute("ALTER TABLE trades ADD COLUMN fill_ts TEXT")

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
                    created_at TEXT NOT NULL,
                    fill_ts TEXT,
                    entry_hash TEXT NOT NULL DEFAULT '',
                    prev_hash TEXT NOT NULL DEFAULT ''
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

    def _tip_hash(self, conn: sqlite3.Connection) -> str:
        row = conn.execute(
            "SELECT entry_hash FROM trades WHERE entry_hash != '' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return str(row["entry_hash"]) if row and row["entry_hash"] else _GENESIS

    def append_trade(
        self,
        record: TradeRecord,
        *,
        created_at: str | None = None,
        fill_ts: str | None = None,
    ) -> int:
        ts = created_at or _utc_now()
        venue_ts = fill_ts or ts
        with self._connect() as conn:
            prev = self._tip_hash(conn)
            payload = {
                "pair": record.pair,
                "side": record.side,
                "stake_usd": record.stake_usd,
                "pnl_usd": record.pnl_usd,
                "signal_source": record.signal_source,
                "rationale": record.rationale,
                "exchange_trade_id": record.exchange_trade_id,
                "exchange": record.exchange,
                "bot_id": record.bot_id,
                "created_at": ts,
                "fill_ts": venue_ts,
            }
            digest = _entry_hash(prev, payload)
            cur = conn.execute(
                """
                INSERT INTO trades (pair, side, stake_usd, pnl_usd, signal_source,
                    rationale, exchange_trade_id, exchange, bot_id, created_at, fill_ts,
                    entry_hash, prev_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ts,
                    venue_ts,
                    digest,
                    prev,
                ),
            )
            return require_row_id(cur)

    def realized_pnl_since(self, since_utc: str) -> float:
        """Sum of realized PnL on trades created at or after since_utc (ISO-8601, UTC offset)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl_usd), 0.0) FROM trades WHERE created_at >= ?",
                (since_utc,),
            ).fetchone()
        return float(row[0])

    def first_profitable_trade(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT pair, side, stake_usd, pnl_usd, signal_source, rationale,
                       exchange_trade_id, exchange, bot_id, created_at, fill_ts,
                       entry_hash, prev_hash
                FROM trades WHERE pnl_usd > 0
                ORDER BY created_at ASC LIMIT 1
                """
            ).fetchone()
            return dict(row) if row else None

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
            rows = conn.execute(
                "SELECT pair, side, stake_usd, pnl_usd, signal_source, rationale, "
                "exchange_trade_id, exchange, bot_id, created_at, fill_ts, "
                "entry_hash, prev_hash "
                "FROM trades ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_trades_chained(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT pair, side, stake_usd, pnl_usd, signal_source, rationale, "
                "exchange_trade_id, exchange, bot_id, created_at, fill_ts, "
                "entry_hash, prev_hash FROM trades ORDER BY id ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def verify_hash_chain(self) -> bool:
        prev = _GENESIS
        for row in self.list_trades_chained():
            if not row.get("entry_hash"):
                continue
            if str(row.get("prev_hash") or "") != prev:
                return False
            payload = {
                "pair": row["pair"],
                "side": row["side"],
                "stake_usd": row["stake_usd"],
                "pnl_usd": row["pnl_usd"],
                "signal_source": row["signal_source"],
                "rationale": row["rationale"],
                "exchange_trade_id": row["exchange_trade_id"],
                "exchange": row["exchange"],
                "bot_id": row["bot_id"],
                "created_at": row["created_at"],
                "fill_ts": row.get("fill_ts") or row["created_at"],
            }
            if _entry_hash(prev, payload) != row["entry_hash"]:
                return False
            prev = str(row["entry_hash"])
        return True

    def list_trades_for_bot(self, bot_id: int, limit: int = 500) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT pair, side, stake_usd, pnl_usd, signal_source, rationale, "
                "exchange_trade_id, exchange, bot_id, created_at, fill_ts, "
                "entry_hash, prev_hash "
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
