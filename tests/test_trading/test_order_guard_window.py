"""RISK-06: windowed failure rate trips; success must not clear the window."""

from __future__ import annotations

from pathlib import Path

from trendalgo.trading.order_guard import FAILURE_WINDOW_S, MAX_FAILURES_IN_WINDOW
from trendalgo.trading.order_journal import OrderJournal


def test_alternating_success_failure_still_trips(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "journal.db")
    t0 = 1_700_000_000.0
    for i in range(10):
        journal.record_success("kraken")
        journal.record_failure("kraken", f"err-{i}", now=t0 + i)
    assert journal.is_halted("kraken")
    # Three failures inside the window are enough; successes never cleared them.
    assert MAX_FAILURES_IN_WINDOW == 3
    assert FAILURE_WINDOW_S == 60.0


def test_failures_outside_window_do_not_count(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "journal.db")
    t0 = 1_700_000_000.0
    journal.record_failure("kraken", "old-1", now=t0)
    journal.record_failure("kraken", "old-2", now=t0 + 1)
    journal.record_failure("kraken", "fresh", now=t0 + FAILURE_WINDOW_S + 5)
    assert journal.is_halted("kraken") is False
