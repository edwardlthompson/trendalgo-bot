"""S16 billing attribution by exchange and bot."""

from __future__ import annotations

from trendalgo.billing.engine import process_journal_trades
from trendalgo.billing.store import BillingStore
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.journal import TradeJournal, TradeRecord
from trendalgo.risk.manager import RiskManager


def test_journal_tags_flow_to_ledger(tmp_path) -> None:
    billing = BillingStore(tmp_path / "billing.db")
    journal = TradeJournal(tmp_path / "journal.db")
    risk = RiskManager(limits=RiskLimits(), wallet_usd=1000)
    journal.append_trade(
        TradeRecord(
            pair="BTC/USD",
            side="sell",
            stake_usd=100,
            pnl_usd=20.0,
            signal_source="grid-trading",
            rationale="exit",
            exchange_trade_id="gemini-t1",
            exchange="gemini",
            bot_id=2,
        )
    )
    result = process_journal_trades(billing, journal, risk)
    assert result["attribution_by_exchange"].get("gemini", 0) >= 0
    ledger = billing.list_ledger(result["period"])
    assert ledger
    assert ledger[0]["exchange"] == "gemini"
    assert ledger[0]["bot_id"] == 2
