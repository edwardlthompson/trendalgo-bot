"""Strategy decay monitor (SIM-11 + FEAT-06).

SIM-11: trail detection + alert. FEAT-06: per-bot health score and de-risk action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DeRiskAction = Literal["none", "reduce_size", "pause"]


@dataclass(frozen=True)
class DecayAlert:
    bot_id: int
    live_net_pct: float
    fitted_net_pct: float
    trades: int
    margin: float
    message: str


@dataclass(frozen=True)
class DecayHealth:
    bot_id: int
    score: float
    action: DeRiskAction
    live_net_pct: float
    fitted_net_pct: float
    trades: int


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


def health_score(
    *,
    live_net_pct: float,
    fitted_net_pct: float,
    trades: int,
    min_trades: int = 20,
) -> float:
    """0..1 health. Below ``min_trades`` returns 1.0 (insufficient evidence)."""
    if trades < min_trades:
        return 1.0
    if fitted_net_pct <= 0:
        return 1.0 if live_net_pct >= 0 else 0.0
    ratio = live_net_pct / fitted_net_pct
    if ratio >= 1.0:
        return 1.0
    if ratio <= 0.0:
        return 0.0
    return float(ratio)


def derisk_action(
    score: float, *, pause_below: float = 0.35, reduce_below: float = 0.6
) -> DeRiskAction:
    """Map health score to a de-risk action at threshold."""
    if score < pause_below:
        return "pause"
    if score < reduce_below:
        return "reduce_size"
    return "none"


def evaluate_health(
    *,
    bot_id: int,
    live_net_pct: float,
    fitted_net_pct: float,
    trades: int,
    min_trades: int = 20,
    pause_below: float = 0.35,
    reduce_below: float = 0.6,
) -> DecayHealth:
    score = health_score(
        live_net_pct=live_net_pct,
        fitted_net_pct=fitted_net_pct,
        trades=trades,
        min_trades=min_trades,
    )
    return DecayHealth(
        bot_id=bot_id,
        score=score,
        action=derisk_action(score, pause_below=pause_below, reduce_below=reduce_below),
        live_net_pct=live_net_pct,
        fitted_net_pct=fitted_net_pct,
        trades=trades,
    )
