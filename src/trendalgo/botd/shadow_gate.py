"""Shadow promotion gates (LIVE-02 param retune + FEAT-02 generic strategy go-live).

LIVE-02: holdout margin + shadow window before swapping live params.
FEAT-02: any strategy must clear bots shadow progress (and clean divergence) before live.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trendalgo.bots.shadow_gate import (
    DEFAULT_MIN_DAYS,
    DEFAULT_MIN_SIGNALS,
    ShadowProgress,
    shadow_gate_allows_go_live,
)

DEFAULT_HOLDOUT_MARGIN = 0.01  # absolute Net % points
DEFAULT_SHADOW_BARS = 20
MAX_CONSECUTIVE_LOSSES = 2
OVERRIDE_PHRASE = "I ACCEPT EARLY GO-LIVE"


def beats_incumbent(
    *,
    candidate_holdout: float,
    incumbent_holdout: float,
    margin: float = DEFAULT_HOLDOUT_MARGIN,
) -> bool:
    """Candidate must beat incumbent by ``margin``, not a rounding error."""
    return float(candidate_holdout) >= float(incumbent_holdout) + float(margin)


@dataclass
class ShadowPromotionState:
    live_params: dict[str, Any]
    known_good: dict[str, Any]
    pending_params: dict[str, Any] | None = None
    shadow_bars_required: int = DEFAULT_SHADOW_BARS
    consecutive_losses: int = 0
    shadow_bars_seen: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "live_params": dict(self.live_params),
            "known_good": dict(self.known_good),
            "pending_params": dict(self.pending_params) if self.pending_params else None,
            "shadow_bars_required": self.shadow_bars_required,
            "consecutive_losses": self.consecutive_losses,
            "shadow_bars_seen": self.shadow_bars_seen,
        }


def begin_shadow(
    state: ShadowPromotionState,
    *,
    candidate_params: dict[str, Any],
    candidate_holdout: float,
    incumbent_holdout: float,
    margin: float = DEFAULT_HOLDOUT_MARGIN,
) -> tuple[ShadowPromotionState, str]:
    """Enter shadow only when holdout margin clears; else keep incumbent."""
    if not beats_incumbent(
        candidate_holdout=candidate_holdout,
        incumbent_holdout=incumbent_holdout,
        margin=margin,
    ):
        return state, "reject_margin"
    state.pending_params = dict(candidate_params)
    state.consecutive_losses = 0
    state.shadow_bars_seen = 0
    return state, "shadow"


def record_shadow_window(
    state: ShadowPromotionState,
    *,
    pnl: float,
    bars: int,
) -> tuple[ShadowPromotionState, str]:
    """Accumulate shadow bars; two consecutive losing windows revert exact known-good."""
    if state.pending_params is None:
        return state, "idle"
    if bars < state.shadow_bars_required:
        state.shadow_bars_seen += bars
        return state, "hold"
    state.shadow_bars_seen += bars
    if pnl < 0:
        state.consecutive_losses += 1
        if state.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
            # Exact prior parameter set (copy, not alias).
            state.live_params = dict(state.known_good)
            state.pending_params = None
            state.consecutive_losses = 0
            state.shadow_bars_seen = 0
            return state, "revert"
        return state, "hold"
    # Winning window → promote pending to live and refresh known-good.
    state.consecutive_losses = 0
    promoted = dict(state.pending_params)
    state.live_params = promoted
    state.known_good = dict(promoted)
    state.pending_params = None
    state.shadow_bars_seen = 0
    return state, "promote"


@dataclass(frozen=True)
class StrategyShadowState:
    """Shadow readiness for one strategy identity (bot id, plan id, or slug)."""

    strategy_id: str
    days: float
    signals: int
    divergence_clean: bool = True
    min_days: float = DEFAULT_MIN_DAYS
    min_signals: int = DEFAULT_MIN_SIGNALS

    def progress(self) -> ShadowProgress:
        return ShadowProgress(
            days=self.days,
            signals=self.signals,
            min_days=self.min_days,
            min_signals=self.min_signals,
        )


def promotion_allowed(
    state: StrategyShadowState,
    *,
    typed_override: str | None = None,
    require_clean_divergence: bool = True,
) -> tuple[bool, str]:
    """Generic go-live: blocked until shadow clears (FEAT-02)."""
    ok, reason = shadow_gate_allows_go_live(state.progress(), typed_override=typed_override)
    if not ok:
        return False, reason
    if require_clean_divergence and not state.divergence_clean:
        if typed_override == OVERRIDE_PHRASE:
            return True, "typed_override_dirty_divergence"
        return False, "shadow_divergence"
    return True, reason if reason != "shadow_ok" else "shadow_ok"
