"""RISK-01: slippage and fees charge traded notional on both sides, not PnL."""

from __future__ import annotations

from datetime import UTC, datetime

from trendalgo.backtest.slippage import apply_slippage
from trendalgo.schemas.backtest_result import BacktestResult, BacktestTradeSummary


def _result(*, stake: float, profit_abs: float, profit_ratio: float) -> BacktestResult:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return BacktestResult(
        strategy="x",
        pair="BTC/USD",
        timeframe="5m",
        timerange="20240101",
        total_trades=1,
        profit_total=profit_abs,
        profit_total_pct=profit_abs / stake,
        max_drawdown=0.0,
        trades=[
            BacktestTradeSummary(
                pair="BTC/USD",
                profit_ratio=profit_ratio,
                profit_abs=profit_abs,
                open_date=now,
                close_date=now,
            )
        ],
        metadata={"stake_usd": stake},
    )


def test_slippage_charges_notional_both_sides_not_pnl() -> None:
    # 0.1% slip on $10k notional, $2 profit → ~$20 slip cost (entry+exit), not ~$0.002.
    base = _result(stake=10_000.0, profit_abs=2.0, profit_ratio=0.0002)
    adj = apply_slippage(base, slippage_pct=0.001, fee_pct=0.0)
    assert adj.trades[0].profit_abs == -18.0
    assert adj.profit_total == -18.0
    assert adj.profit_total_pct == -18.0 / 10_000.0


def test_slippage_recomputes_max_drawdown_and_profit_ratio() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    base = BacktestResult(
        strategy="x",
        pair="BTC/USD",
        timeframe="5m",
        timerange="20240101",
        total_trades=2,
        profit_total=100.0,
        profit_total_pct=0.1,
        max_drawdown=0.0,
        trades=[
            BacktestTradeSummary(
                pair="BTC/USD",
                profit_ratio=0.2,
                profit_abs=200.0,
                open_date=now,
                close_date=now,
            ),
            BacktestTradeSummary(
                pair="BTC/USD",
                profit_ratio=-0.1,
                profit_abs=-100.0,
                open_date=now,
                close_date=now,
            ),
        ],
        metadata={"stake_usd": 1000.0},
    )
    adj = apply_slippage(base, slippage_pct=0.01, fee_pct=0.0)
    # Each trade: 2 * 1000 * 0.01 = 20 notional cost.
    assert adj.trades[0].profit_abs == 180.0
    assert adj.trades[1].profit_abs == -120.0
    assert adj.trades[0].profit_ratio == 0.18
    assert adj.profit_total == 60.0
    assert adj.profit_total_pct == 0.06
    # Equity path: 1000 → 1180 → 1060; peak 1180; dd = (1180-1060)/1180.
    assert adj.max_drawdown == round((1180.0 - 1060.0) / 1180.0, 4)
