"""Chaos dry-run: unknown order must not blind re-send (Phase 0)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.trading.order_journal import OrderJournal, new_client_id


def test_pending_order_survives_for_reconcile(tmp_path: Path) -> None:
    journal = OrderJournal(tmp_path / "orders.db")
    cid = new_client_id()
    journal.record_intent(cid, "kraken", "BTC/USD", "buy", 0.01)
    unresolved = journal.unresolved("kraken")
    assert any(row["client_id"] == cid for row in unresolved)
    # A second intent with a new client id is fine; same client must stay one row.
    again = journal.unresolved("kraken")
    assert sum(1 for row in again if row["client_id"] == cid) == 1
