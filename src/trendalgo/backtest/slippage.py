"""Backtest slippage simulation (T13; RISK-01 notional both sides)."""

from __future__ import annotations

from trendalgo.schemas.backtest_result import BacktestResult, BacktestTradeSummary


def _stake_usd(result: BacktestResult) -> float:
    meta = result.metadata
    for key in ("stake_usd", "initial_wallet", "wallet_usd"):
        raw = meta.get(key)
        if raw is not None:
            stake = float(raw)
            if stake > 0:
                return stake
    return 1000.0


def _trade_notional(trade: BacktestTradeSummary, default_stake: float) -> float:
    if trade.profit_ratio != 0.0:
        return abs(trade.profit_abs / trade.profit_ratio)
    return default_stake


def _max_drawdown(stake: float, profits: list[float]) -> float | None:
    if not profits:
        return None
    equity = stake
    peak = stake
    worst = 0.0
    for pnl in profits:
        equity += pnl
        if equity > peak:
            peak = equity
        if peak > 0:
            worst = max(worst, (peak - equity) / peak)
    return round(worst, 4)


def apply_slippage(result: BacktestResult, slippage_pct: float, fee_pct: float) -> BacktestResult:
    stake = _stake_usd(result)
    adjusted: list[BacktestTradeSummary] = []
    profits: list[float] = []
    total = 0.0
    for trade in result.trades:
        notional = _trade_notional(trade, stake)
        # Entry + exit: charge notional * pct on both sides.
        slip_cost = notional * slippage_pct * 2.0
        fee_cost = notional * fee_pct * 2.0
        new_profit = trade.profit_abs - slip_cost - fee_cost
        new_ratio = (new_profit / notional) if notional else 0.0
        adjusted.append(
            BacktestTradeSummary(
                pair=trade.pair,
                profit_ratio=round(new_ratio, 6),
                profit_abs=round(new_profit, 4),
                open_date=trade.open_date,
                close_date=trade.close_date,
            )
        )
        profits.append(new_profit)
        total += new_profit
    return BacktestResult(
        strategy=result.strategy,
        pair=result.pair,
        timeframe=result.timeframe,
        timerange=result.timerange,
        total_trades=result.total_trades,
        profit_total=round(total, 4),
        profit_total_pct=round(total / stake, 4) if stake else 0.0,
        max_drawdown=_max_drawdown(stake, profits),
        trades=adjusted,
        metadata={**result.metadata, "slippage_pct": slippage_pct, "fee_pct": fee_pct},
    )
