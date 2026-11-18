"""Fee-aware order routing — prefer maker when the strategy tolerates it (FEAT-03)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OrderStyle = Literal["maker", "taker"]


@dataclass(frozen=True)
class FeeTier:
    maker_pct: float
    taker_pct: float

    def fee_for(self, style: OrderStyle) -> float:
        return self.maker_pct if style == "maker" else self.taker_pct


@dataclass(frozen=True)
class RoutingDecision:
    style: OrderStyle
    expected_fee_pct: float
    reason: str


def expected_cost_pct(tiers: FeeTier, style: OrderStyle) -> float:
    """Objective term: expected fee fraction for the chosen style."""
    return float(tiers.fee_for(style))


def prefer_maker_when_tolerated(
    tiers: FeeTier,
    *,
    resting_entry_ok: bool,
    max_maker_wait_bars: int = 0,
    urgency_bars: int = 0,
) -> RoutingDecision:
    """Prefer maker when resting is tolerated and wait budget covers urgency.

    ``resting_entry_ok`` is the strategy flag that a limit/post-only entry is fine.
    ``max_maker_wait_bars`` is how long the strategy will wait to rest; ``urgency_bars``
    is how soon the signal expires. Maker wins only when wait >= urgency and maker
    fee is strictly cheaper (or equal — still prefer maker for rebate/tier progress).
    """
    if not resting_entry_ok:
        return RoutingDecision("taker", expected_cost_pct(tiers, "taker"), "resting_not_tolerated")
    if max_maker_wait_bars < urgency_bars:
        return RoutingDecision("taker", expected_cost_pct(tiers, "taker"), "urgency_exceeds_wait")
    maker = expected_cost_pct(tiers, "maker")
    taker = expected_cost_pct(tiers, "taker")
    if maker <= taker:
        return RoutingDecision("maker", maker, "maker_cheaper_or_equal")
    return RoutingDecision("taker", taker, "taker_cheaper")
