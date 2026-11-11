"""Shared paper/dry-run fill model (SIM-10)."""

from __future__ import annotations

from trendalgo.backtest.sim_fill import apply_entry_slip, apply_exit_slip


def paper_fill_price(
    signal_price: float,
    *,
    side: str,
    slippage_bps: float = 0.0,
    next_bar_price: float | None = None,
    fill_offset: int = 1,
) -> float:
    """Match backtest fill_offset/slip semantics for live paper + dry-run.

    When ``fill_offset>=1`` and ``next_bar_price`` is provided, fill there;
    otherwise fill at ``signal_price`` (offset 0 / tip bar).
    """
    raw = float(signal_price)
    if int(fill_offset) >= 1 and next_bar_price is not None:
        raw = float(next_bar_price)
    side_l = str(side).lower()
    if side_l in {"buy", "long", "entry"}:
        return apply_entry_slip(raw, slippage_bps)
    return apply_exit_slip(raw, slippage_bps)
