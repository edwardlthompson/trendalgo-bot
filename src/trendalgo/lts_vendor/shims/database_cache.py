"""OHLCV price cache for the vendored LTS backtester (the ``database.cache`` shim).

Series live in a process-local map and, when a database path is given, in a SQLite file
that every backtest worker shares, so repeated runs skip the exchange download.

Freshness: an entry expires ``max_age_hours`` after it was fetched. Hourly series must
also reach the present: the newest candle must have opened within ``_HOURLY_NEWEST_LAG_S``,
otherwise a truncated download would be trusted for the full TTL. Rows flagged
``synthetic`` are never written to disk, so a Kraken outage cannot poison later runs.

Persistence is best-effort. A file that cannot be opened or written disables SQLite for
that instance and the cache continues in memory, so a backtest never fails on the cache.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

Key = tuple[str, str, str]
Entry = tuple[float, list[dict[str, Any]]]

_BUSY_TIMEOUT_S = 10.0
_HOURLY_NEWEST_LAG_S = 3 * 3600.0
_SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlcv_series (
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (exchange, symbol, timeframe)
)
"""


def _now() -> float:
    """Epoch seconds. Tests replace this to simulate time passing."""
    return time.time()


def _key(exchange: str, symbol: str, timeframe: str) -> Key:
    return (exchange.lower(), symbol.upper(), timeframe.lower())


@contextmanager
def _connect(path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path, timeout=_BUSY_TIMEOUT_S)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _newest_ts(rows: list[dict[str, Any]]) -> float | None:
    try:
        return max(float(row["ts"]) for row in rows)
    except (KeyError, TypeError, ValueError):
        return None


def _is_fresh(timeframe: str, entry: Entry, now: float, max_age_s: float) -> bool:
    fetched_at, rows = entry
    age = now - fetched_at
    if not rows or age < 0 or age > max_age_s:
        return False
    if timeframe.lower() != "1h":
        return True
    newest = _newest_ts(rows)
    return newest is not None and now - newest <= _HOURLY_NEWEST_LAG_S


def _init_db(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _connect(path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(_SCHEMA)
    except (sqlite3.Error, OSError) as exc:
        logger.warning("price cache SQLite disabled, using memory only: %s", exc)
        return False
    return True


def _write_entry(path: Path, key: Key, entry: Entry) -> None:
    fetched_at, rows = entry
    try:
        body = json.dumps(rows, separators=(",", ":"))
        with _connect(path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ohlcv_series "
                "(exchange, symbol, timeframe, fetched_at, payload) VALUES (?, ?, ?, ?, ?)",
                (*key, fetched_at, body),
            )
    except (sqlite3.Error, OSError, TypeError, ValueError) as exc:
        logger.warning("price cache write skipped for %s: %s", key, exc)


def _read_entry(path: Path, key: Key) -> Entry | None:
    try:
        with _connect(path) as conn:
            found = conn.execute(
                "SELECT fetched_at, payload FROM ohlcv_series "
                "WHERE exchange = ? AND symbol = ? AND timeframe = ?",
                key,
            ).fetchone()
        if found is None:
            return None
        return float(found[0]), json.loads(found[1])
    except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
        logger.warning("price cache read skipped for %s: %s", key, exc)
        return None


class PriceCache:
    """OHLCV rows keyed by (exchange, symbol, timeframe); SQLite-backed when a path is given."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path: Path | None = Path(db_path) if db_path else None
        self._memory: dict[Key, Entry] = {}
        if self.db_path is not None and not _init_db(self.db_path):
            self.db_path = None

    def cache_ohlcv_rows(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        rows: list[dict[str, Any]],
        source: str = "api",
    ) -> int:
        key = _key(exchange, symbol, timeframe)
        payload = [dict(r) for r in rows]
        for row in payload:
            row.setdefault("source", source)
        entry: Entry = (_now(), payload)
        self._memory[key] = entry
        if self.db_path is not None and not any(row.get("synthetic") for row in payload):
            _write_entry(self.db_path, key, entry)
        return len(payload)

    def get_ohlcv_rows(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        max_age_hours: float = 6,
    ) -> tuple[bool, list[dict[str, Any]] | None]:
        key = _key(exchange, symbol, timeframe)
        now = _now()
        max_age_s = float(max_age_hours) * 3600.0
        entry = self._memory.get(key)
        if entry is None or not _is_fresh(timeframe, entry, now, max_age_s):
            entry = _read_entry(self.db_path, key) if self.db_path is not None else None
        if entry is None or not _is_fresh(timeframe, entry, now, max_age_s):
            return False, None
        self._memory[key] = entry
        return True, entry[1]

    def close(self) -> None:
        self._memory.clear()
