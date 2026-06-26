"""Risk limits configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RiskLimits(BaseModel):
    """Sprint 2 defaults — override via config/risk.limits.json."""

    max_stake_usd: float = Field(100.0, gt=0)
    max_stake_pct: float = Field(0.02, gt=0, le=1.0)
    daily_loss_cap_usd: float = Field(50.0, gt=0)
    circuit_breaker_drawdown_pct: float = Field(0.10, gt=0, le=1.0)
    max_open_trades: int = Field(1, ge=1)

    model_config = {"extra": "forbid"}
