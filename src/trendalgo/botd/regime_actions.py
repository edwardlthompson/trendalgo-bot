"""Regime flip → defensive actions before re-fit (LIVE-04)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RegimeActionState:
    regime: str
    size_mult: float = 1.0
    stop_mult: float = 1.0  # <1 tightens stop distance
    in_cash: bool = False
    candidate_regime: str | None = None
    candidate_bars: int = 0
    prior_size_mult: float = 1.0
    prior_stop_mult: float = 1.0


@dataclass(frozen=True)
class RegimeAction:
    kind: str
    allow_refit: bool


def on_regime_observation(
    state: RegimeActionState,
    *,
    regime: str,
    stable_bars_required: int = 3,
) -> tuple[RegimeActionState, RegimeAction]:
    """One-bar blip → size cut only; sustained flip escalates to refit_ready."""
    if regime == state.regime:
        if state.candidate_regime is not None:
            # Blip ended before stability — restore sizing/stops.
            state.size_mult = state.prior_size_mult
            state.stop_mult = state.prior_stop_mult
            state.in_cash = False
            state.candidate_regime = None
            state.candidate_bars = 0
            return state, RegimeAction("restore", False)
        return state, RegimeAction("none", False)

    if state.candidate_regime != regime:
        state.candidate_regime = regime
        state.candidate_bars = 1
        state.prior_size_mult = state.size_mult
        state.prior_stop_mult = state.stop_mult
        state.size_mult = min(state.size_mult, 0.5)
        return state, RegimeAction("size_cut", False)

    state.candidate_bars += 1
    if state.candidate_bars == 2:
        state.stop_mult = min(state.stop_mult, 0.7)
        return state, RegimeAction("tighten", False)

    if state.candidate_bars >= stable_bars_required:
        state.in_cash = True
        state.regime = regime
        state.candidate_regime = None
        state.candidate_bars = 0
        return state, RegimeAction("refit_ready", True)

    state.in_cash = True
    return state, RegimeAction("cash", False)
