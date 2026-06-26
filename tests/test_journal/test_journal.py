from pathlib import Path

from trendalgo.risk.journal import TradeJournal, TradeRecord


def test_journal_and_idempotency(tmp_path: Path) -> None:
    db = tmp_path / "journal.db"
    journal = TradeJournal(db)
    tid = journal.append_trade(
        TradeRecord(
            pair="BTC/USD",
            side="long",
            stake_usd=100,
            pnl_usd=5,
            signal_source="MultiTFExample",
            rationale="rsi oversold",
            exchange_trade_id="kraken-1",
        )
    )
    key = "close:kraken-1:2024-01-01"
    assert journal.record_fee_hook(tid, key, {"pnl": 5}) is True
    assert journal.record_fee_hook(tid, key, {"pnl": 5}) is False
    assert journal.fee_hook_exists(key) is True
    assert journal.count_trades() == 1
