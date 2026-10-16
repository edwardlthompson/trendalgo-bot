"""Entry sizing for the streaming port. Same expressions as the engine's helpers, so results match bit for bit."""

from __future__ import annotations

from trendalgo.lts_vendor.backtesting.models import BacktestConfig


def stake_notional(config: BacktestConfig, free_cash: float) -> float:
    """Cash committed to one entry. all_in commits all of it, as the engine does."""
    if config.stake_mode == "fixed_usd":
        return min(float(config.stake_value or 0.0), free_cash)
    if config.stake_mode == "percent":
        return free_cash * float(config.stake_value or 0.0) / 100.0
    return free_cash


def with_reserve(proceeds: float, reserve: float) -> float:
    """Free cash after a close. A zero reserve returns the proceeds unchanged."""
    return proceeds if reserve == 0.0 else proceeds + reserve
