"""RISK-02: peak/breaker equity is wallet only (balance+open), never wallet+daily_pnl."""

from __future__ import annotations

import pytest

from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager
from trendalgo.risk.metrics import metrics_summary


def test_refresh_never_adds_daily_pnl_on_top_of_wallet() -> None:
    mgr = RiskManager(RiskLimits(circuit_breaker_drawdown_pct=0.10), wallet_usd=1000.0)
    mgr.set_equity(balance_usd=900.0, open_position_usd=100.0)  # wallet = 1000
    mgr.state.daily_pnl_usd = -200.0
    mgr._refresh_peak_and_breaker()
    # Equity for breaker is wallet (1000), not 1000-200=800 — no trip at 10%.
    assert mgr.state.circuit_breaker_active is False
    assert mgr.state.peak_equity_usd == 1000.0


def test_set_equity_drop_trips_breaker_without_daily_pnl() -> None:
    mgr = RiskManager(RiskLimits(circuit_breaker_drawdown_pct=0.10), wallet_usd=1000.0)
    mgr.set_equity(balance_usd=800.0, open_position_usd=0.0)
    assert mgr.state.circuit_breaker_active is True


def test_metrics_equity_is_wallet_only() -> None:
    mgr = RiskManager(RiskLimits(), wallet_usd=1000.0)
    mgr.state.daily_pnl_usd = 25.0
    m = metrics_summary(mgr)
    assert m["equity_usd"] == 1000.0
    assert m["daily_pnl_usd"] == 25.0


@pytest.mark.parametrize(
    ("balance", "open_pos", "daily"),
    [
        (1000.0, 0.0, -200.0),
        (4500.0, 500.0, 75.0),
        (0.0, 250.0, -10.0),
        (99.5, 0.5, 1e5),
    ],
)
def test_peak_input_never_sees_equity_twice(balance: float, open_pos: float, daily: float) -> None:
    mgr = RiskManager(RiskLimits(circuit_breaker_drawdown_pct=1.0), wallet_usd=1.0)
    mgr.set_equity(balance_usd=balance, open_position_usd=open_pos)
    mgr.state.daily_pnl_usd = daily
    before = mgr.state.peak_equity_usd
    mgr._refresh_peak_and_breaker()
    expected = balance + open_pos
    assert mgr.wallet_usd == expected
    assert mgr.state.peak_equity_usd == max(before, expected)
