"""Core data models for deterministic backtesting."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

# all_in stakes all free cash (the golden default). fixed_usd stakes a dollar amount.
# percent stakes a share of free cash. Idle cash stays in the account until the position closes.
STAKE_MODES = ("all_in", "fixed_usd", "percent")


def _check_trailing_stop(pct: float, enabled: bool) -> None:
    """An enabled trailing stop keeps the 1.0 floor. A disabled one only refuses negatives (L2)."""
    if enabled and pct < 1.0:
        raise ValueError("trailing_stop_loss_pct must be >= 1.0")
    if not enabled and pct < 0.0:
        raise ValueError("trailing_stop_loss_pct must be >= 0 when the trailing stop is disabled")


def _validate_stake(mode: str, value: float | None) -> tuple[str, float | None]:
    if mode not in STAKE_MODES:
        raise ValueError(f"stake_mode must be one of {', '.join(STAKE_MODES)}")
    if mode == "all_in":
        if value is not None:
            raise ValueError("stake_value applies only to fixed_usd or percent")
        return mode, None
    if value is None or not math.isfinite(value) or value <= 0:
        raise ValueError("stake_value must be a positive number")
    if mode == "percent" and value > 100.0:
        raise ValueError("stake_value for percent must be at most 100")
    return mode, float(value)


@dataclass
class BacktestConfig:
    starting_capital: float
    fee_bps_round_trip: float
    trailing_stop_loss_pct: float
    take_profit_pct: float
    trailing_take_profit_pct: float
    trailing_stop_enabled: bool
    stake_mode: str
    stake_value: float | None

    def __init__(
        self,
        starting_capital: float = 1000.0,
        fee_bps_round_trip: float = 52.0,
        trailing_stop_loss_pct: float = 1.0,
        take_profit_pct: float = 0.0,
        trailing_take_profit_pct: float = 0.0,
        trailing_stop_pct: float | None = None,
        trailing_stop_enabled: bool = True,
        stake_mode: str = "all_in",
        stake_value: float | None = None,
    ) -> None:
        self.starting_capital = float(starting_capital)
        self.fee_bps_round_trip = float(fee_bps_round_trip)
        self.trailing_stop_enabled = bool(trailing_stop_enabled)
        resolved_tsl = float(
            trailing_stop_loss_pct if trailing_stop_pct is None else trailing_stop_pct
        )
        _check_trailing_stop(resolved_tsl, self.trailing_stop_enabled)
        self.trailing_stop_loss_pct = resolved_tsl
        self.take_profit_pct = float(take_profit_pct)
        self.trailing_take_profit_pct = float(trailing_take_profit_pct)
        self.stake_mode, self.stake_value = _validate_stake(stake_mode, stake_value)

    @property
    def trailing_stop_pct(self) -> float:
        return float(self.trailing_stop_loss_pct)

    @trailing_stop_pct.setter
    def trailing_stop_pct(self, value: float) -> None:
        resolved = float(value)
        _check_trailing_stop(resolved, self.trailing_stop_enabled)
        self.trailing_stop_loss_pct = resolved

    @property
    def side_fee_rate(self) -> float:
        return (self.fee_bps_round_trip / 10000.0) / 2.0


@dataclass
class Trade:
    entry_time: str
    entry_price: float
    entry_fee: float
    quantity: float
    exit_time: str
    exit_price: float
    exit_fee: float
    pnl_dollars: float
    pnl_pct: float
    exit_reason: str


@dataclass
class BacktestResult:
    final_equity: float
    net_pct: float
    total_trades: int
    win_pct: float
    trades: list[Trade] = field(default_factory=list)


@dataclass
class BuyHoldResult:
    final_equity: float
    net_pct: float
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
