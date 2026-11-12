"""FEAT-01: deterministic journal replay reproduces equity bit-for-bit."""

from __future__ import annotations

from pathlib import Path

from trendalgo.risk.journal import TradeJournal, TradeRecord
from trendalgo.trading.journal_replay import (
    equity_fingerprint,
    replay_equity,
    replay_journal_equity,
)


def _seed(journal: TradeJournal) -> None:
    journal.append_trade(
        TradeRecord(
            pair="BTC/USD",
            side="buy",
            stake_usd=100.0,
            pnl_usd=-1.25,
            signal_source="test",
            rationale="entry fee",
            exchange_trade_id="t1",
            exchange="kraken",
            bot_id=1,
        ),
        created_at="2026-01-01T00:00:00+00:00",
    )
    journal.append_trade(
        TradeRecord(
            pair="BTC/USD",
            side="sell",
            stake_usd=100.0,
            pnl_usd=12.5,
            signal_source="test",
            rationale="exit",
            exchange_trade_id="t2",
            exchange="kraken",
            bot_id=1,
        ),
        created_at="2026-01-01T01:00:00+00:00",
    )
    journal.append_trade(
        TradeRecord(
            pair="ETH/USD",
            side="sell",
            stake_usd=50.0,
            pnl_usd=-3.0,
            signal_source="test",
            rationale="stop",
            exchange_trade_id="t3",
            exchange="kraken",
            bot_id=1,
        ),
        created_at="2026-01-01T02:00:00+00:00",
    )


def test_replay_equity_bit_for_bit(tmp_path: Path) -> None:
    src = TradeJournal(tmp_path / "a.db")
    _seed(src)
    first = replay_journal_equity(src, starting_equity_usd=1000.0, bot_id=1)
    # Fresh store + re-seed from the same records must match exactly.
    dst = TradeJournal(tmp_path / "b.db")
    for row in src.list_trades_for_bot(1):
        dst.append_trade(
            TradeRecord(
                pair=str(row["pair"]),
                side=str(row["side"]),
                stake_usd=float(row["stake_usd"]),
                pnl_usd=float(row["pnl_usd"]),
                signal_source=str(row["signal_source"]),
                rationale=str(row["rationale"]),
                exchange_trade_id=str(row["exchange_trade_id"]),
                exchange=str(row.get("exchange") or ""),
                bot_id=int(row["bot_id"]) if row.get("bot_id") is not None else None,
            ),
            created_at=str(row["created_at"]),
        )
    second = replay_journal_equity(dst, starting_equity_usd=1000.0, bot_id=1)
    assert equity_fingerprint(first) == equity_fingerprint(second)
    assert first[-1].equity_usd == 1008.25


def test_replay_from_records_is_order_stable() -> None:
    records = [
        TradeRecord(
            pair="BTC/USD",
            side="sell",
            stake_usd=10.0,
            pnl_usd=1.0,
            signal_source="t",
            rationale="a",
            exchange_trade_id="a",
        ),
        TradeRecord(
            pair="BTC/USD",
            side="sell",
            stake_usd=10.0,
            pnl_usd=2.0,
            signal_source="t",
            rationale="b",
            exchange_trade_id="b",
        ),
    ]
    a = replay_equity(records, starting_equity_usd=100.0)
    b = replay_equity(records, starting_equity_usd=100.0)
    assert equity_fingerprint(a) == equity_fingerprint(b)
    assert [p.equity_usd for p in a] == [100.0, 101.0, 103.0]
