"""Per-exchange guard: consecutive order failures and the halt flag (E2, E3).

Three rejected or unknown orders in a row halt new buys. An orphan order or an unexplained
balance change halts too, until an operator resets it. Sells are never refused by the halt (R5).
A new halt is announced once: the balance sync reads pending_halt_notice and marks it announced,
so a halt set by a buy is reported too. The methods are mixed into OrderJournal, which owns the
SQLite connection and the lock they use.
"""

from __future__ import annotations

import sqlite3
import threading

MAX_CONSECUTIVE_FAILURES = 3
# A halt that starts is unannounced until a balance sync reports it; one that continues is not.
_START_UNANNOUNCED = "announced = CASE WHEN halted = 1 THEN announced ELSE 0 END"


class GuardRows:
    """Failure counter and halt flag per exchange, kept in the exchange_guard table."""

    _conn: sqlite3.Connection
    _lock: threading.Lock

    def record_failure(self, exchange: str, error: str) -> int:
        """Count one failed order. Halts new buys at the limit. Returns the new count."""
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO exchange_guard (exchange, consecutive_failures, halted, last_error) "
                "VALUES (?, 1, 0, ?) ON CONFLICT(exchange) DO UPDATE SET "
                "consecutive_failures = consecutive_failures + 1, "
                "last_error = excluded.last_error",
                (exchange, error),
            )
            self._conn.execute(
                "UPDATE exchange_guard SET " + _START_UNANNOUNCED + ", halted = 1 "
                "WHERE exchange = ? AND consecutive_failures >= ?",
                (exchange, MAX_CONSECUTIVE_FAILURES),
            )
            row = self._conn.execute(
                "SELECT consecutive_failures FROM exchange_guard WHERE exchange = ?",
                (exchange,),
            ).fetchone()
        return int(row[0])

    def record_success(self, exchange: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE exchange_guard SET consecutive_failures = 0 WHERE exchange = ?",
                (exchange,),
            )

    def is_halted(self, exchange: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT halted FROM exchange_guard WHERE exchange = ?", (exchange,)
            ).fetchone()
        return bool(row and row[0])

    def halt(self, exchange: str, reason: str) -> None:
        """Halt new buys on one exchange until an operator resets it (orphans, balances, E3)."""
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO exchange_guard "
                "(exchange, consecutive_failures, halted, last_error, announced) "
                "VALUES (?, 0, 1, ?, 0) ON CONFLICT(exchange) DO UPDATE SET "
                + _START_UNANNOUNCED
                + ", halted = 1, last_error = excluded.last_error",
                (exchange, reason),
            )

    def reset_halt(self, exchange: str) -> None:
        """Operator action: clear the halt and the failure count for one exchange."""
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE exchange_guard SET halted = 0, consecutive_failures = 0 WHERE exchange = ?",
                (exchange,),
            )

    def pending_halt_notice(self, exchange: str) -> str | None:
        """Reason for a halt that no balance sync has announced yet, else None (E3)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT last_error FROM exchange_guard "
                "WHERE exchange = ? AND halted = 1 AND announced = 0",
                (exchange,),
            ).fetchone()
        return None if row is None else str(row[0] or "halted")

    def mark_halt_announced(self, exchange: str) -> None:
        """Record that the current halt has been reported, so it is not reported again."""
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE exchange_guard SET announced = 1 WHERE exchange = ?", (exchange,)
            )
