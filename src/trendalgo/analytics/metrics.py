"""Performance metrics — Sharpe, Sortino, Calmar, profit factor (T1, T13)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from trendalgo.schemas.backtest_result import BacktestTradeSummary


@dataclass(frozen=True)
class PerformanceMetrics:
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    profit_factor: float
    win_rate: float
    max_drawdown: float
    total_trades: int
    profit_total: float


def _returns_from_trades(trades: list[BacktestTradeSummary], initial_balance: float) -> list[float]:
    balance = initial_balance
    returns: list[float] = []
    for trade in trades:
        if balance <= 0:
            break
        ret = trade.profit_abs / balance
        returns.append(ret)
        balance += trade.profit_abs
    return returns


def _max_drawdown_from_trades(trades: list[BacktestTradeSummary], initial_balance: float) -> float:
    equity = initial_balance
    peak = initial_balance
    max_dd = 0.0
    for trade in trades:
        equity += trade.profit_abs
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    return round(max_dd, 4)


def compute_metrics(
    trades: list[BacktestTradeSummary],
    *,
    initial_balance: float = 1000.0,
    periods_per_year: float = 365.0,
) -> PerformanceMetrics:
    if not trades:
        return PerformanceMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0)

    returns = _returns_from_trades(trades, initial_balance)
    wins = [t for t in trades if t.profit_abs > 0]
    losses = [t for t in trades if t.profit_abs < 0]
    gross_profit = sum(t.profit_abs for t in wins)
    gross_loss = abs(sum(t.profit_abs for t in losses))
    profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else float("inf")
    win_rate = round(len(wins) / len(trades), 4)
    profit_total = round(sum(t.profit_abs for t in trades), 2)
    max_dd = _max_drawdown_from_trades(trades, initial_balance)

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    std = math.sqrt(variance) if variance > 0 else 0.0
    downside = [min(r, 0.0) for r in returns]
    down_var = sum(r * r for r in downside) / len(downside) if downside else 0.0
    down_std = math.sqrt(down_var) if down_var > 0 else 0.0

    scale = math.sqrt(periods_per_year)
    sharpe = round((mean / std) * scale, 4) if std > 0 else 0.0
    sortino = round((mean / down_std) * scale, 4) if down_std > 0 else 0.0
    total_return = profit_total / initial_balance if initial_balance > 0 else 0.0
    calmar = round(total_return / max_dd, 4) if max_dd > 0 else 0.0

    return PerformanceMetrics(
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        profit_factor=profit_factor if profit_factor != float("inf") else 999.0,
        win_rate=win_rate,
        max_drawdown=max_dd,
        total_trades=len(trades),
        profit_total=profit_total,
    )


def equity_curve(
    trades: list[BacktestTradeSummary],
    *,
    initial_balance: float = 1000.0,
) -> list[dict[str, float | str]]:
    """Time series for Lightweight Charts (unix seconds + equity)."""
    points: list[dict[str, float | str]] = []
    equity = initial_balance
    for trade in sorted(trades, key=lambda t: t.close_date or t.open_date):
        ts = trade.close_date or trade.open_date
        equity += trade.profit_abs
        points.append({"time": int(ts.timestamp()), "value": round(equity, 2)})
    if not points:
        points.append({"time": 0, "value": initial_balance})
    return points
