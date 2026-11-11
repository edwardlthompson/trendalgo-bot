"""RISK-03: can_open_trade rolls the UTC day inline without a scheduler tick."""

from __future__ import annotations

from datetime import UTC, datetime

from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager


def test_three_days_without_scheduler_still_roll_the_cap() -> None:
    mgr = RiskManager(RiskLimits(daily_loss_cap_usd=50), wallet_usd=1000.0)
    day1 = datetime(2026, 10, 8, 15, 0, tzinfo=UTC)
    mgr.sync_daily_pnl(-60.0, day1)
    assert mgr.can_open_trade(now=day1) == (False, "daily loss cap exceeded")

    day2 = datetime(2026, 10, 9, 10, 0, tzinfo=UTC)
    ok, reason = mgr.can_open_trade(now=day2)
    assert ok is True
    assert reason == "ok"
    assert mgr.state.day_key == "2026-10-09"
    assert mgr.state.daily_pnl_usd == 0.0

    mgr.state.daily_pnl_usd = -60.0
    assert mgr.can_open_trade(now=day2)[0] is False

    day3 = datetime(2026, 10, 10, 1, 0, tzinfo=UTC)
    assert mgr.can_open_trade(now=day3) == (True, "ok")
    assert mgr.state.day_key == "2026-10-10"
    assert mgr.state.daily_pnl_usd == 0.0
