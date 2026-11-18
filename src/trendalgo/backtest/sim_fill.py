"""Shared fill helpers for backtest + dry-run (SIM-01/02/10).

Known omissions (SIM-02): no funding, no min notional, no partial fills.
"""

from __future__ import annotations


def slip_factor(slippage_bps: float) -> float:
    return max(0.0, float(slippage_bps)) / 10_000.0


def apply_entry_slip(price: float, slippage_bps: float) -> float:
    """Long entry: trader pays more."""
    return float(price) * (1.0 + slip_factor(slippage_bps))


def apply_exit_slip(price: float, slippage_bps: float) -> float:
    """Long exit: trader receives less."""
    return float(price) * (1.0 - slip_factor(slippage_bps))


def gap_through_long_exit(stop_price: float, bar_open: float) -> float:
    """Worse of stop and open for a long stop-out (lower is worse)."""
    return min(float(stop_price), float(bar_open))
