"""Per-exchange guard: windowed order failures and the halt flag (E2, E3; RISK-06).

Three rejected or unknown orders inside FAILURE_WINDOW_S halt new buys. An orphan order or
an unexplained balance change halts too, until an operator resets it. Sells are never refused
by the halt (R5). record_success must not clear the failure window — a flapping exchange still
trips. A new halt is announced once: the balance sync reads pending_halt_notice and marks it
announced. The methods are mixed into OrderJournal, which owns the SQLite connection and lock.
"""

from __future__ import annotations

import sqlite3
import threading
import time

FAILURE_WINDOW_S = 60.0
MAX_FAILURES_IN_WINDOW = 3
# Back-compat alias used by existing tests and callers.
MAX_CONSECUTIVE_FAILURES = MAX_FAILURES_IN_WINDOW
# A halt that starts is unannounced until a balance sync reports it; one that continues is not.
_START_UNANNOUNCED = "announced = CASE WHEN halted = 1 THEN announced ELSE 0 END"


class GuardRows:
    """Failure window and halt flag per exchange, kept in exchange_guard tables."""

    _conn: sqlite3.Connection
    _lock: threading.Lock

    def record_failure(self, exchange: str, error: str, *, now: float | None = None) -> int:
        """Record one failed order. Halts new buys at MAX_FAILURES_IN_WINDOW in the window."""
        ts = time.time() if now is None else now
        cutoff = ts - FAILURE_WINDOW_S
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO exchange_guard_failures (exchange, failed_at) VALUES (?, ?)",
                (exchange, ts),
            )
            self._conn.execute(
                "DELETE FROM exchange_guard_failures WHERE exchange = ? AND failed_at < ?",
                (exchange, cutoff),
            )
            count_row = self._conn.execute(
                "SELECT COUNT(*) FROM exchange_guard_failures "
                "WHERE exchange = ? AND failed_at >= ?",
                (exchange, cutoff),
            ).fetchone()
            count = int(count_row[0])
            self._conn.execute(
                "INSERT INTO exchange_guard (exchange, consecutive_failures, halted, last_error) "
                "VALUES (?, ?, 0, ?) ON CONFLICT(exchange) DO UPDATE SET "
                "consecutive_failures = excluded.consecutive_failures, "
                "last_error = excluded.last_error",
                (exchange, count, error),
            )
            if count >= MAX_FAILURES_IN_WINDOW:
                self._conn.execute(
                    "UPDATE exchange_guard SET " + _START_UNANNOUNCED + ", halted = 1 "
                    "WHERE exchange = ?",
                    (exchange,),
                )
        return count

    def record_success(self, exchange: str) -> None:
        """A fill succeeded. RISK-06: do not clear the failure window."""
        return

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
        """Operator action: clear the halt and the failure window for one exchange."""
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM exchange_guard_failures WHERE exchange = ?", (exchange,)
            )
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
