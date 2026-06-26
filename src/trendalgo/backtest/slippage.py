"""Backtest slippage simulation (T13)."""

from __future__ import annotations

from trendalgo.schemas.backtest_result import BacktestResult, BacktestTradeSummary


def apply_slippage(result: BacktestResult, slippage_pct: float, fee_pct: float) -> BacktestResult:
    adjusted: list[BacktestTradeSummary] = []
    total = 0.0
    for trade in result.trades:
        slip_cost = abs(trade.profit_abs) * slippage_pct
        fee_cost = abs(trade.profit_abs) * fee_pct
        new_profit = trade.profit_abs - slip_cost - fee_cost
        adjusted.append(
            BacktestTradeSummary(
                pair=trade.pair,
                profit_ratio=trade.profit_ratio,
                profit_abs=round(new_profit, 4),
                open_date=trade.open_date,
                close_date=trade.close_date,
            )
        )
        total += new_profit
    return BacktestResult(
        strategy=result.strategy,
        pair=result.pair,
        timeframe=result.timeframe,
        timerange=result.timerange,
        total_trades=result.total_trades,
        profit_total=round(total, 4),
        profit_total_pct=round(total / 1000.0, 4),
        max_drawdown=result.max_drawdown,
        trades=adjusted,
        metadata={**result.metadata, "slippage_pct": slippage_pct, "fee_pct": fee_pct},
    )
