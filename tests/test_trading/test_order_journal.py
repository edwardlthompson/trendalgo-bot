"""E2, E3: order journal rows, unresolved orders, and the per-exchange halt."""

from __future__ import annotations

from pathlib import Path

from trendalgo.trading.order_guard import MAX_CONSECUTIVE_FAILURES
from trendalgo.trading.order_journal import OrderJournal, new_client_id


def test_intent_is_stored_then_updated(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "journal.db")
    journal.record_intent("ta0000000000000001", "kraken", "BTC/USD", "buy", 0.0005)
    row = journal.get("ta0000000000000001")
    assert row is not None
    assert row["status"] == "pending"
    journal.set_status("ta0000000000000001", "submitted", exchange_order_id="O-1")
    row = journal.get("ta0000000000000001")
    assert row is not None
    assert row["status"] == "submitted"
    assert row["exchange_order_id"] == "O-1"
    assert journal.get("missing") is None


def test_unresolved_lists_only_pending_and_unknown_rows_for_one_exchange(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "journal.db")
    journal.record_intent("ta0000000000000001", "kraken", "BTC/USD", "buy", 0.1)
    journal.record_intent("ta0000000000000002", "kraken", "BTC/USD", "buy", 0.1)
    journal.set_status("ta0000000000000002", "unknown")
    journal.record_intent("ta0000000000000003", "kraken", "BTC/USD", "buy", 0.1)
    journal.set_status("ta0000000000000003", "submitted")
    journal.record_intent("ta0000000000000004", "gemini", "BTC/USD", "buy", 0.1)
    ids = sorted(row["client_id"] for row in journal.unresolved("kraken"))
    assert ids == ["ta0000000000000001", "ta0000000000000002"]


def test_failures_halt_at_the_limit(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "journal.db")
    for attempt in range(MAX_CONSECUTIVE_FAILURES - 1):
        journal.record_failure("kraken", f"error {attempt}")
        assert not journal.is_halted("kraken")
    journal.record_failure("kraken", "last error")
    assert journal.is_halted("kraken")
    assert not journal.is_halted("gemini")


def test_success_resets_the_count(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "journal.db")
    journal.record_failure("kraken", "error")
    journal.record_failure("kraken", "error")
    journal.record_success("kraken")
    journal.record_failure("kraken", "error")
    assert not journal.is_halted("kraken")


def test_reset_clears_the_halt(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "journal.db")
    for _ in range(MAX_CONSECUTIVE_FAILURES):
        journal.record_failure("kraken", "error")
    assert journal.is_halted("kraken")
    journal.reset_halt("kraken")
    assert not journal.is_halted("kraken")


def test_halt_survives_a_restart_and_clears_on_reset(tmp_path: Path) -> None:
    path = tmp_path / "journal.db"
    journal = OrderJournal(path)
    journal.halt("kraken", "orphan order on the exchange")
    assert OrderJournal(path).is_halted("kraken")
    journal.reset_halt("kraken")
    assert not OrderJournal(path).is_halted("kraken")


def test_halt_survives_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "journal.db"
    journal = OrderJournal(path)
    for _ in range(MAX_CONSECUTIVE_FAILURES):
        journal.record_failure("kraken", "error")
    assert OrderJournal(path).is_halted("kraken")


def test_a_new_halt_is_announced_once(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "journal.db")
    assert journal.pending_halt_notice("kraken") is None
    journal.halt("kraken", "orphan order on the exchange")
    assert journal.pending_halt_notice("kraken") == "orphan order on the exchange"
    journal.mark_halt_announced("kraken")
    journal.halt("kraken", "another reason while still halted")
    assert journal.pending_halt_notice("kraken") is None  # the same halt is not announced again
    journal.reset_halt("kraken")
    assert journal.pending_halt_notice("kraken") is None
    journal.halt("kraken", "orphan order on the exchange")
    assert journal.pending_halt_notice("kraken") == "orphan order on the exchange"


def test_a_halt_from_failures_is_announced_too(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "journal.db")
    for _ in range(MAX_CONSECUTIVE_FAILURES):
        journal.record_failure("kraken", "insufficient funds")
    assert journal.pending_halt_notice("kraken") == "insufficient funds"
    journal.mark_halt_announced("kraken")
    journal.record_failure("kraken", "another refusal")  # a sell refused while halted
    assert journal.pending_halt_notice("kraken") is None


def test_client_ids_are_unique_and_short() -> None:
    ids = {new_client_id() for _ in range(1000)}
    assert len(ids) == 1000
    assert all(len(client_id) == 18 for client_id in ids)
