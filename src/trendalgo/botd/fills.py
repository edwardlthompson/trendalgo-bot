"""Fills ledger (ADR-0017). Each fill carries owner_id, the live flag, plan_version, and the bundle hash.

Shadow fills are recorded for divergence checks but never produce a statement line.
Live fills may emit Telegram + outbox trade alerts when host secrets are present.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from trendalgo.botd.owner import assert_owner

FILLS_SCHEMA = """
CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id TEXT NOT NULL,
    live INTEGER NOT NULL,
    plan_version INTEGER NOT NULL,
    bundle_hash TEXT NOT NULL,
    pair TEXT NOT NULL,
    side TEXT NOT NULL,
    amount REAL NOT NULL,
    price REAL NOT NULL,
    fee_usd REAL NOT NULL DEFAULT 0,
    realized_pnl_usd REAL NOT NULL DEFAULT 0,
    filled_at TEXT NOT NULL
);
"""


class FillsLedger:
    def __init__(
        self,
        db_path: Path,
        *,
        host_owner_id: str,
        secrets_root: Path | None = None,
        on_live_fill: Callable[..., None] | None = None,
    ) -> None:
        self.db_path = db_path
        self.host_owner_id = host_owner_id
        self.secrets_root = secrets_root if secrets_root is not None else db_path.parent
        self._on_live_fill = on_live_fill
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(FILLS_SCHEMA)

    def record(
        self,
        *,
        owner_id: str | None,
        live: bool,
        plan_version: int,
        bundle_hash: str,
        pair: str,
        side: str,
        amount: float,
        price: float,
        filled_at: str,
        fee_usd: float = 0.0,
        realized_pnl_usd: float = 0.0,
    ) -> int:
        """Record one fill. A foreign owner is refused before anything is written."""
        assert_owner(owner_id, self.host_owner_id)
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO fills (owner_id, live, plan_version, bundle_hash, pair, side, amount, "
                "price, fee_usd, realized_pnl_usd, filled_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    owner_id,
                    int(live),
                    plan_version,
                    bundle_hash,
                    pair,
                    side,
                    amount,
                    price,
                    fee_usd,
                    realized_pnl_usd,
                    filled_at,
                ),
            )
            fill_id = int(cur.lastrowid or 0)
        if live:
            self._emit_trade_alert(
                fill_id=fill_id,
                pair=pair,
                side=side,
                amount=amount,
                price=price,
                fee_usd=fee_usd,
                realized_pnl_usd=realized_pnl_usd,
                plan_version=plan_version,
            )
        return fill_id

    def _emit_trade_alert(
        self,
        *,
        fill_id: int,
        pair: str,
        side: str,
        amount: float,
        price: float,
        fee_usd: float,
        realized_pnl_usd: float,
        plan_version: int,
    ) -> None:
        if self._on_live_fill is not None:
            self._on_live_fill(
                fill_id=fill_id,
                pair=pair,
                side=side,
                amount=amount,
                price=price,
                fee_usd=fee_usd,
                realized_pnl_usd=realized_pnl_usd,
                plan_version=plan_version,
            )
            return
        from trendalgo.botd.trade_notify import notify_fill

        notify_fill(
            self.secrets_root,
            pair=pair,
            side=side,
            amount=amount,
            price=price,
            fee_usd=fee_usd,
            realized_pnl_usd=realized_pnl_usd,
            plan_version=plan_version,
            live=True,
        )

    def statement_lines(self, *, start_iso: str, end_iso: str) -> list[dict[str, Any]]:
        """Live fills in [start, end). Shadow fills are excluded by construction."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM fills WHERE live = 1 AND filled_at >= ? AND filled_at < ? "
                "ORDER BY id",
                (start_iso, end_iso),
            ).fetchall()
            return [dict(row) for row in rows]
