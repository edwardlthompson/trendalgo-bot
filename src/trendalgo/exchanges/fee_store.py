"""SQLite persistence for exchange fee schedules."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = _REPO_ROOT / "config" / "exchange_fees.json"
_SEED_PATH = SEED_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS exchange_fees (
    exchange_id TEXT PRIMARY KEY,
    ccxt_id TEXT NOT NULL,
    taker_pct REAL NOT NULL,
    maker_pct REAL NOT NULL,
    tier TEXT NOT NULL DEFAULT 'retail_default',
    source TEXT NOT NULL,
    source_url TEXT NOT NULL DEFAULT '',
    fetched_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exchange_fee_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at TEXT NOT NULL,
    exchange_id TEXT NOT NULL,
    status TEXT NOT NULL,
    prev_taker REAL,
    prev_maker REAL,
    new_taker REAL,
    new_maker REAL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_fee_checks_at ON exchange_fee_checks(checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_fee_checks_ex ON exchange_fee_checks(exchange_id, checked_at DESC);
"""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _data_dir() -> Path:
    return Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))


class FeeStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM exchange_fees").fetchone()
            return int(row[0]) if row else 0

    def upsert(
        self,
        exchange_id: str,
        *,
        ccxt_id: str,
        taker_pct: float,
        maker_pct: float,
        tier: str,
        source: str,
        source_url: str = "",
        fetched_at: str | None = None,
    ) -> None:
        now = _utc_now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO exchange_fees (
                    exchange_id, ccxt_id, taker_pct, maker_pct, tier, source,
                    source_url, fetched_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exchange_id) DO UPDATE SET
                    ccxt_id=excluded.ccxt_id,
                    taker_pct=excluded.taker_pct,
                    maker_pct=excluded.maker_pct,
                    tier=excluded.tier,
                    source=excluded.source,
                    source_url=excluded.source_url,
                    fetched_at=excluded.fetched_at,
                    updated_at=excluded.updated_at
                """,
                (
                    exchange_id,
                    ccxt_id,
                    taker_pct,
                    maker_pct,
                    tier,
                    source,
                    source_url,
                    fetched_at or now,
                    now,
                ),
            )

    def get(self, exchange_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM exchange_fees WHERE exchange_id = ?",
                (exchange_id.lower(),),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM exchange_fees ORDER BY exchange_id ASC",
            ).fetchall()
        return [dict(r) for r in rows]

    def record_check(
        self,
        exchange_id: str,
        status: str,
        *,
        prev_taker: float | None = None,
        prev_maker: float | None = None,
        new_taker: float | None = None,
        new_maker: float | None = None,
        detail: str = "",
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO exchange_fee_checks (
                    checked_at, exchange_id, status, prev_taker, prev_maker,
                    new_taker, new_maker, detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _utc_now(),
                    exchange_id,
                    status,
                    prev_taker,
                    prev_maker,
                    new_taker,
                    new_maker,
                    detail,
                ),
            )

    def last_global_check(self) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT checked_at FROM exchange_fee_checks ORDER BY id DESC LIMIT 1",
            ).fetchone()
        return str(row[0]) if row else None

    def recent_checks(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM exchange_fee_checks
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def seed_from_json(self, path: Path | None = None) -> int:
        seed_path = path or _SEED_PATH
        if not seed_path.is_file():
            raise FileNotFoundError(f"fee seed not found: {seed_path}")
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        tier = str(data.get("tier", "retail_default"))
        exchanges = data.get("exchanges") or {}
        from trendalgo.exchanges.registry import load_registry

        registry = load_registry()
        seeded = 0
        for entry in registry.exchanges:
            row = exchanges.get(entry.id)
            if row is None:
                continue
            self.upsert(
                entry.id,
                ccxt_id=entry.ccxt_id,
                taker_pct=float(row["taker_pct"]),
                maker_pct=float(row["maker_pct"]),
                tier=tier,
                source="documented",
                source_url=str(row.get("source_url", "")),
            )
            self.record_check(entry.id, "seeded", detail="documented fees from exchange_fees.json")
            seeded += 1
        return seeded


@lru_cache(maxsize=1)
def get_fee_store(data_dir: Path | None = None) -> FeeStore:
    base = data_dir or _data_dir()
    store = FeeStore(base / "exchange_fees.db")
    if store.count() == 0:
        try:
            store.seed_from_json()
        except FileNotFoundError:
            pass
    return store


def reset_fee_store() -> None:
    get_fee_store.cache_clear()
