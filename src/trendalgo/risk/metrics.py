"""Exposure, daily P/L, and drawdown metrics."""

from __future__ import annotations

from trendalgo.risk.manager import RiskManager


def metrics_summary(
    manager: RiskManager, open_exposure_usd: float = 0.0
) -> dict[str, float | bool | str]:
    equity = manager.wallet_usd + manager.state.daily_pnl_usd
    peak = manager.state.peak_equity_usd or equity
    drawdown_pct = round((peak - equity) / peak, 4) if peak > 0 else 0.0
    can_trade, reason = manager.can_open_trade()
    return {
        "wallet_usd": manager.wallet_usd,
        "equity_usd": round(equity, 2),
        "daily_pnl_usd": round(manager.state.daily_pnl_usd, 2),
        "drawdown_pct": drawdown_pct,
        "open_exposure_usd": round(open_exposure_usd, 2),
        "circuit_breaker_active": manager.state.circuit_breaker_active,
        "paused": manager.state.paused,
        "can_trade": can_trade,
        "block_reason": reason,
    }


def risk_metrics(
    manager: RiskManager, open_exposure_usd: float = 0.0
) -> dict[str, float | bool | str]:
    return metrics_summary(manager, open_exposure_usd)
