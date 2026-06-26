"""Backtest runner — sample engine for Sprint 3 UI; native adapter in trading/backtest/."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trendalgo.schemas.backtest_result import BacktestResult, BacktestTradeSummary


def run_sample_backtest(
    *,
    strategy: str,
    pair: str,
    timeframe: str,
    timerange: str,
) -> BacktestResult:
    """Deterministic sample backtest for dashboard / API tests."""
    now = datetime.now(UTC).replace(microsecond=0)
    trades = [
        BacktestTradeSummary(
            pair=pair,
            profit_ratio=0.012,
            profit_abs=12.0,
            open_date=now - timedelta(days=5),
            close_date=now - timedelta(days=4, hours=20),
        ),
        BacktestTradeSummary(
            pair=pair,
            profit_ratio=-0.008,
            profit_abs=-8.0,
            open_date=now - timedelta(days=3),
            close_date=now - timedelta(days=2, hours=18),
        ),
        BacktestTradeSummary(
            pair=pair,
            profit_ratio=0.021,
            profit_abs=21.0,
            open_date=now - timedelta(days=1),
            close_date=now - timedelta(hours=6),
        ),
    ]
    profit_total = sum(t.profit_abs for t in trades)
    return BacktestResult(
        strategy=strategy,
        pair=pair,
        timeframe=timeframe,
        timerange=timerange,
        total_trades=len(trades),
        profit_total=profit_total,
        profit_total_pct=round(profit_total / 1000.0, 4),
        max_drawdown=0.018,
        trades=trades,
        metadata={"engine": "sample", "dry_run": True},
    )
