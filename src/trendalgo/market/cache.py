"""SQLite cache for OHLCV close prices."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from trendalgo.market.types import PricePoint

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_candles (
    source TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    ts INTEGER NOT NULL,
    close REAL NOT NULL,
    PRIMARY KEY (source, symbol, timeframe, ts)
);
CREATE INDEX IF NOT EXISTS idx_price_lookup
    ON price_candles (symbol, timeframe, ts);
"""


class PriceCache:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def upsert(self, source: str, symbol: str, timeframe: str, points: list[PricePoint]) -> None:
        if not points:
            return
        rows = [(source, symbol, timeframe, p.time, p.close) for p in points]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO price_candles (source, symbol, timeframe, ts, close)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, symbol, timeframe, ts) DO UPDATE SET close = excluded.close
                """,
                rows,
            )

    def query(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> list[PricePoint]:
        since_ts = int(since.replace(tzinfo=UTC).timestamp())
        until_ts = int(until.replace(tzinfo=UTC).timestamp())
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ts, close FROM price_candles
                WHERE source = ? AND symbol = ? AND timeframe = ?
                  AND ts >= ? AND ts <= ?
                ORDER BY ts
                """,
                (source, symbol, timeframe, since_ts, until_ts),
            ).fetchall()
        return [PricePoint(time=int(r[0]), close=float(r[1])) for r in rows]
