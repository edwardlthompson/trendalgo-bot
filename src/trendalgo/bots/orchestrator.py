"""Multi-bot orchestrator (T10)."""

from __future__ import annotations

import json
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
    created_at TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '1h'
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
        if "timeframe" not in cols:
            conn.execute("ALTER TABLE bots ADD COLUMN timeframe TEXT NOT NULL DEFAULT '1h'")
        if "equity_mode" not in cols:
            conn.execute("ALTER TABLE bots ADD COLUMN equity_mode TEXT NOT NULL DEFAULT 'manual'")
        if "equity_input" not in cols:
            conn.execute("ALTER TABLE bots ADD COLUMN equity_input REAL NOT NULL DEFAULT 1000")
        if "ta_params" not in cols:
            conn.execute("ALTER TABLE bots ADD COLUMN ta_params TEXT NOT NULL DEFAULT '{}'")

    def _row_to_bot(self, row: sqlite3.Row) -> dict[str, Any]:
        ta_raw = row["ta_params"] if "ta_params" in row.keys() else "{}"
        try:
            ta_params = json.loads(ta_raw) if ta_raw else {}
        except json.JSONDecodeError:
            ta_params = {}
        return {
            "id": int(row["id"]),
            "label": row["label"],
            "strategy_id": row["strategy_id"],
            "pair": row["pair"],
            "enabled": bool(row["enabled"]),
            "equity_usd": float(row["equity_usd"]),
            "engine": row["engine"] if "engine" in row.keys() else "native",
            "exchange": row["exchange"] if "exchange" in row.keys() else "kraken",
            "timeframe": row["timeframe"] if "timeframe" in row.keys() else "1h",
            "equity_mode": row["equity_mode"] if "equity_mode" in row.keys() else "manual",
            "equity_input": float(row["equity_input"])
            if "equity_input" in row.keys()
            else float(row["equity_usd"]),
            "ta_params": ta_params,
        }

    def list_bots(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM bots ORDER BY id").fetchall()
            return [self._row_to_bot(r) for r in rows]

    def add_bot(
        self,
        label: str,
        strategy_id: str,
        pair: str,
        equity_usd: float = 1000,
        *,
        engine: str = "native",
        exchange: str = "kraken",
        timeframe: str = "60",
        enabled: bool = True,
        ta_params: dict[str, Any] | None = None,
    ) -> int:
        params_json = json.dumps(ta_params or {})
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO bots (label, strategy_id, pair, enabled, equity_usd, engine, exchange, "
                "created_at, timeframe, equity_mode, equity_input, ta_params) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    label,
                    strategy_id,
                    pair,
                    int(enabled),
                    equity_usd,
                    engine,
                    exchange,
                    _utc_now(),
                    timeframe,
                    "quote",
                    equity_usd,
                    params_json,
                ),
            )
            return int(cur.lastrowid)

    def set_enabled(self, bot_id: int, enabled: bool) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE bots SET enabled = ? WHERE id = ?", (int(enabled), bot_id))

    def get_bot(self, bot_id: int) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_bot(row)

    def update_bot(
        self,
        bot_id: int,
        *,
        label: str,
        strategy_id: str,
        pair: str,
        equity_usd: float,
        timeframe: str = "1h",
        exchange: str = "kraken",
        equity_mode: str = "manual",
        equity_input: float | None = None,
        ta_params: dict[str, Any] | None = None,
    ) -> None:
        resolved_input = equity_input if equity_input is not None else equity_usd
        params_json = json.dumps(ta_params or {})
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE bots
                SET label = ?, strategy_id = ?, pair = ?, equity_usd = ?, timeframe = ?,
                    exchange = ?, equity_mode = ?, equity_input = ?, ta_params = ?
                WHERE id = ?
                """,
                (
                    label,
                    strategy_id,
                    pair,
                    equity_usd,
                    timeframe,
                    exchange,
                    equity_mode,
                    resolved_input,
                    params_json,
                    bot_id,
                ),
            )

    def delete_bot(self, bot_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
            if count <= 1:
                raise ValueError("cannot delete the last bot")
            conn.execute("DELETE FROM bots WHERE id = ?", (bot_id,))

    def count_enabled(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM bots WHERE enabled = 1").fetchone()
            return int(row[0])
