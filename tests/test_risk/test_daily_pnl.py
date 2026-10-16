"""R2: daily PnL comes from journaled fills, and the day starts again at UTC midnight."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trendalgo.risk.config import RiskLimits
from trendalgo.risk.journal import TradeJournal, TradeRecord
from trendalgo.risk.manager import RiskManager, utc_day_start


def _fill(journal: TradeJournal, pnl: float, at: datetime, fill_id: str) -> None:
    record = TradeRecord(
        pair="BTC/USD",
        side="sell",
        stake_usd=100,
        pnl_usd=pnl,
        signal_source="test",
        rationale="test fill",
        exchange_trade_id=fill_id,
        exchange="kraken",
        bot_id=1,
    )
    journal.append_trade(record, created_at=at.isoformat())


def _sync(mgr: RiskManager, journal: TradeJournal, now: datetime) -> None:
    mgr.sync_daily_pnl(journal.realized_pnl_since(utc_day_start(now).isoformat()), now)


def test_fills_trip_the_daily_loss_cap(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "journal.db")
    now = datetime(2026, 10, 9, 15, 0, tzinfo=UTC)
    _fill(journal, -60.0, now.replace(hour=14), "fill-a")
    mgr = RiskManager(RiskLimits(daily_loss_cap_usd=50), wallet_usd=1000)
    _sync(mgr, journal, now)
    assert mgr.state.daily_pnl_usd == -60.0
    assert mgr.can_open_trade() == (False, "daily loss cap exceeded")


def test_the_cap_starts_again_at_utc_midnight(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "journal.db")
    _fill(journal, -60.0, datetime(2026, 10, 8, 23, 50, tzinfo=UTC), "fill-late")
    mgr = RiskManager(RiskLimits(daily_loss_cap_usd=50), wallet_usd=1000)
    _sync(mgr, journal, datetime(2026, 10, 8, 23, 55, tzinfo=UTC))
    assert mgr.can_open_trade()[0] is False
    _sync(mgr, journal, datetime(2026, 10, 9, 0, 10, tzinfo=UTC))
    assert mgr.state.day_key == "2026-10-09"
    assert mgr.state.daily_pnl_usd == 0.0
    assert mgr.can_open_trade() == (True, "ok")


def test_a_restart_recovers_the_day_from_the_journal(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "journal.db")
    now = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
    _fill(journal, -60.0, now.replace(hour=9), "fill-morning")
    after_restart = RiskManager(RiskLimits(daily_loss_cap_usd=50), wallet_usd=1000)
    _sync(after_restart, journal, now)
    assert after_restart.can_open_trade()[0] is False
