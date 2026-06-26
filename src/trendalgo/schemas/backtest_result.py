"""Backtest result JSON schema (T11)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BacktestTradeSummary(BaseModel):
    pair: str
    profit_ratio: float
    profit_abs: float
    open_date: datetime
    close_date: datetime | None = None


class BacktestResult(BaseModel):
    """Contract for UI + API backtest exports."""

    strategy: str
    pair: str
    timeframe: str
    timerange: str
    total_trades: int = 0
    profit_total: float = 0.0
    profit_total_pct: float = 0.0
    max_drawdown: float | None = None
    trades: list[BacktestTradeSummary] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
