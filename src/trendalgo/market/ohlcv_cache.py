"""SQLite cache for full OHLCV candles."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from trendalgo.market.types import OhlcvPoint

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlcv_candles (
    source TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    ts INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    PRIMARY KEY (source, symbol, timeframe, ts)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_lookup
    ON ohlcv_candles (symbol, timeframe, ts);
"""


class OhlcvCache:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def upsert(self, source: str, symbol: str, timeframe: str, points: list[OhlcvPoint]) -> None:
        if not points:
            return
        rows = [
            (source, symbol, timeframe, p.time, p.open, p.high, p.low, p.close, p.volume)
            for p in points
        ]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO ohlcv_candles
                    (source, symbol, timeframe, ts, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, symbol, timeframe, ts) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume
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
    ) -> list[OhlcvPoint]:
        since_ts = int(since.replace(tzinfo=UTC).timestamp())
        until_ts = int(until.replace(tzinfo=UTC).timestamp())
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ts, open, high, low, close, volume FROM ohlcv_candles
                WHERE source = ? AND symbol = ? AND timeframe = ?
                  AND ts >= ? AND ts <= ?
                ORDER BY ts
                """,
                (source, symbol, timeframe, since_ts, until_ts),
            ).fetchall()
        return [
            OhlcvPoint(
                time=int(r[0]),
                open=float(r[1]),
                high=float(r[2]),
                low=float(r[3]),
                close=float(r[4]),
                volume=float(r[5]),
            )
            for r in rows
        ]

    def latest_ts(self, source: str, symbol: str, timeframe: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT MAX(ts) FROM ohlcv_candles
                WHERE source = ? AND symbol = ? AND timeframe = ?
                """,
                (source, symbol, timeframe),
            ).fetchone()
        if row is None or row[0] is None:
            return None
        return int(row[0])

    def count_in_range(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> int:
        since_ts = int(since.replace(tzinfo=UTC).timestamp())
        until_ts = int(until.replace(tzinfo=UTC).timestamp())
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM ohlcv_candles
                WHERE source = ? AND symbol = ? AND timeframe = ?
                  AND ts >= ? AND ts <= ?
                """,
                (source, symbol, timeframe, since_ts, until_ts),
            ).fetchone()
        return int(row[0] if row else 0)
