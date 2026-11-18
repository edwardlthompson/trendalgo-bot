"""BILL-04: journal hash-chain, server recompute, signed statements, forged POST."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from trendalgo.api.app import create_app
from trendalgo.api.state import default_state
from trendalgo.billing.integrity import recompute_statement_from_journal, statement_mismatch
from trendalgo.billing.store import BillingStore
from trendalgo.risk.journal import TradeJournal, TradeRecord


def test_journal_hash_chain_links_entries(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "j.db")
    journal.append_trade(
        TradeRecord("BTC/USD", "long", 100, 10.0, "bot", "a", "t1"),
        created_at="2026-06-10T12:00:00+00:00",
    )
    journal.append_trade(
        TradeRecord("BTC/USD", "long", 100, 20.0, "bot", "b", "t2"),
        created_at="2026-06-11T12:00:00+00:00",
    )
    rows = journal.list_trades_chained()
    assert len(rows) == 2
    assert rows[0]["prev_hash"] == "0" * 64
    assert rows[1]["prev_hash"] == rows[0]["entry_hash"]
    assert journal.verify_hash_chain() is True


def test_delete_local_trade_raises_recompute_mismatch(tmp_path) -> None:
    journal = TradeJournal(tmp_path / "j.db")
    billing = BillingStore(tmp_path / "b.db")
    billing.enroll(0.05, "2026-06-draft-1", "u1")
    billing.set_billing_eligibility("2026-06-01T00:00:00+00:00", "2026-06-01T00:00:00+00:00")
    for ref, pnl in (("t1", 100.0), ("t2", 50.0)):
        journal.append_trade(
            TradeRecord("BTC/USD", "long", 100, pnl, "bot", "x", ref),
            created_at="2026-06-10T12:00:00+00:00",
        )
    stored = recompute_statement_from_journal(billing, journal, period="2026-06")
    assert stored["license_fee_usd"] > 0
    slim = TradeJournal(tmp_path / "j2.db")
    slim.append_trade(
        TradeRecord("BTC/USD", "long", 100, 100.0, "bot", "x", "t1"),
        created_at="2026-06-10T12:00:00+00:00",
    )
    altered = recompute_statement_from_journal(
        BillingStore(tmp_path / "b2.db"), slim, period="2026-06", persist=False
    )
    assert statement_mismatch(stored, altered)


def test_forged_billing_post_rejected() -> None:
    data_dir = Path(tempfile.mkdtemp(prefix="trendalgo-bill04-"))
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir)
    os.environ["TRENDALGO_FEE_SYNC_ON_START"] = "0"
    os.environ.pop("TRENDALGO_OWNER_SECRET", None)
    from trendalgo.exchanges import fees
    from trendalgo.exchanges.fee_store import get_fee_store, reset_fee_store
    from trendalgo.exchanges.fee_sync import ensure_fee_db_ready

    reset_fee_store()
    fees.clear_fee_cache()
    ensure_fee_db_ready(get_fee_store())
    bare = TestClient(create_app(default_state()))
    resp = bare.post("/api/v1/billing/process-trades")
    assert resp.status_code in {401, 403}
