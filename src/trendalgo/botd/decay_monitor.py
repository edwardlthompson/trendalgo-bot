"""Strategy decay monitor stub (SIM-11; shared later with FEAT-06)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DecayAlert:
    bot_id: int
    live_net_pct: float
    fitted_net_pct: float
    trades: int
    margin: float
    message: str


def live_trails_fit(
    *,
    live_net_pct: float,
    fitted_net_pct: float,
    trades: int,
    min_trades: int = 20,
    margin: float = 0.25,
) -> bool:
    """True when live Net % trails fitted expectation by ``margin`` over N trades."""
    if trades < min_trades:
        return False
    return live_net_pct < fitted_net_pct - margin


def maybe_alert(
    *,
    bot_id: int,
    live_net_pct: float,
    fitted_net_pct: float,
    trades: int,
    min_trades: int = 20,
    margin: float = 0.25,
) -> DecayAlert | None:
    if not live_trails_fit(
        live_net_pct=live_net_pct,
        fitted_net_pct=fitted_net_pct,
        trades=trades,
        min_trades=min_trades,
        margin=margin,
    ):
        return None
    return DecayAlert(
        bot_id=bot_id,
        live_net_pct=live_net_pct,
        fitted_net_pct=fitted_net_pct,
        trades=trades,
        margin=margin,
        message=(
            f"bot {bot_id}: live Net {live_net_pct:.2f}% trails fit "
            f"{fitted_net_pct:.2f}% by >{margin:.0%} over {trades} trades"
        ),
    )
