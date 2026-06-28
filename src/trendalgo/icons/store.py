"""SQLite icon registry for exchanges and top coins."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from trendalgo.icons.schema import ICON_REGISTRY_SCHEMA


class IconStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(ICON_REGISTRY_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def upsert_exchange(self, exchange_id: str, brand: str, color: str, icon_path: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO exchange_icons (id, brand, color, icon_path)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    brand = excluded.brand,
                    color = excluded.color,
                    icon_path = excluded.icon_path
                """,
                (exchange_id, brand, color, icon_path),
            )

    def upsert_coin(
        self,
        symbol: str,
        name: str,
        coingecko_id: str,
        icon_url: str,
        market_cap_rank: int | None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO coin_icons (symbol, name, coingecko_id, icon_url, market_cap_rank)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    coingecko_id = excluded.coingecko_id,
                    icon_url = excluded.icon_url,
                    market_cap_rank = excluded.market_cap_rank
                """,
                (symbol.upper(), name, coingecko_id, icon_url, market_cap_rank),
            )

    def get_exchange(self, exchange_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, brand, color, icon_path FROM exchange_icons WHERE id = ?",
                (exchange_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_exchanges(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, brand, color, icon_path FROM exchange_icons ORDER BY brand"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_coin(self, symbol: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT symbol, name, coingecko_id, icon_url, market_cap_rank FROM coin_icons WHERE symbol = ?",
                (symbol.upper(),),
            ).fetchone()
        return dict(row) if row else None

    def coin_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM coin_icons").fetchone()
        return int(row["c"]) if row else 0
