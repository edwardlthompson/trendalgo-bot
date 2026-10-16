"""Order journal (E2, E3).

Every live order intent is written here before it is sent, so an unclear outcome can be
settled by lookup instead of a blind re-send. The per-exchange guard (order_guard.py) halts
new buys only. Exits (sells) are never gated (R5).
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from trendalgo.trading.order_guard import GuardRows
from trendalgo.trading.order_journal_schema import ORDER_COLUMNS, ORDER_SELECT, SCHEMA


class OrderHaltedError(ValueError):
    """New buys are blocked on this exchange. Sells still go through."""


class OrderOutcomeUnknownError(RuntimeError):
    """The order may or may not have been placed. Reconcile before sending anything else."""


def new_client_id() -> str:
    """Short client order id (18 characters), kept short for exchanges with tight limits."""
    return f"ta{uuid.uuid4().hex[:16]}"


class OrderJournal(GuardRows):
    """SQLite store for order intents and the per-exchange failure guard."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._lock = threading.Lock()

    def record_intent(
        self, client_id: str, exchange: str, pair: str, side: str, amount: float
    ) -> None:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO orders (client_id, exchange, pair, side, amount, status, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
                (client_id, exchange, pair, side, amount, now, now),
            )

    def set_status(
        self,
        client_id: str,
        status: str,
        *,
        exchange_order_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE orders SET status = ?, detail = ?, updated_at = ?, "
                "exchange_order_id = COALESCE(?, exchange_order_id) WHERE client_id = ?",
                (status, detail, time.time(), exchange_order_id, client_id),
            )

    def get(self, client_id: str) -> dict[str, Any] | None:
        rows = self._query(ORDER_SELECT + " WHERE client_id = ?", (client_id,))
        return rows[0] if rows else None

    def unresolved(self, exchange: str) -> list[dict[str, Any]]:
        """Orders whose outcome is not settled yet (pending or unknown) on one exchange."""
        return self._query(
            ORDER_SELECT + " WHERE exchange = ? AND status IN ('pending', 'unknown')",
            (exchange,),
        )

    def unfinished(self, exchange: str) -> list[dict[str, Any]]:
        """Orders the exchange accepted whose executed quantity is not final yet."""
        return self._query(
            ORDER_SELECT + " WHERE exchange = ? AND status = 'submitted' "
            "AND exchange_order_id IS NOT NULL",
            (exchange,),
        )

    def set_fills(self, client_id: str, status: str, filled: float) -> None:
        """Record the executed quantity the exchange reports for one order (E3)."""
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE orders SET status = ?, filled = ?, updated_at = ? WHERE client_id = ?",
                (status, filled, time.time(), client_id),
            )

    def rows(self, exchange: str) -> list[dict[str, Any]]:
        """Every order row for one exchange."""
        return self._query(ORDER_SELECT + " WHERE exchange = ?", (exchange,))

    def run(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """Run one statement on a table owned by a trading module, under the lock, then commit."""
        with self._lock, self._conn:
            return self._conn.execute(sql, params).fetchall()

    def count_by_status(self, status: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM orders WHERE status = ?", (status,)
            ).fetchone()
        return int(row[0])

    def _query(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(zip(ORDER_COLUMNS, row, strict=True)) for row in rows]
