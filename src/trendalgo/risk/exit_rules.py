"""Per-strategy exit rules — trailing stop, scale-out (T36)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExitRules(BaseModel):
    trailing_stop_pct: float = Field(0.03, ge=0, le=0.2)
    scale_out_pct: float = Field(0.5, ge=0.1, le=1.0)
    scale_in_enabled: bool = False
    scale_out_enabled: bool = True

    model_config = {"extra": "forbid"}


def scale_position_amount(
    current_stake: float,
    target_pct: float,
    *,
    min_stake: float = 10.0,
) -> float:
    """Suggested adjust_trade_position stake delta."""
    delta = current_stake * target_pct
    return round(max(min_stake, delta), 2)
