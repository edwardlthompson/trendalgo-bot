"""LIVE-02: holdout margin + shadow windows; two losses revert exact prior params."""

from __future__ import annotations

from trendalgo.botd.shadow_divergence import shadow_window_pnl_ok
from trendalgo.botd.shadow_gate import (
    ShadowPromotionState,
    beats_incumbent,
    record_shadow_window,
)


def test_marginal_improvement_does_not_promote() -> None:
    assert not beats_incumbent(candidate_holdout=1.001, incumbent_holdout=1.0, margin=0.01)
    assert beats_incumbent(candidate_holdout=1.05, incumbent_holdout=1.0, margin=0.01)


def test_two_bad_shadow_windows_revert_exact_params() -> None:
    prior = {"q": 0.4, "stop": 2.0}
    candidate = {"q": 0.5, "stop": 2.5}
    state = ShadowPromotionState(
        live_params=dict(prior),
        pending_params=dict(candidate),
        known_good=dict(prior),
        shadow_bars_required=10,
    )
    # First losing window
    state, action = record_shadow_window(state, pnl=-0.5, bars=10)
    assert action == "hold"
    assert state.live_params == prior
    # Second consecutive losing window
    state, action = record_shadow_window(state, pnl=-0.3, bars=10)
    assert action == "revert"
    assert state.live_params == prior
    assert state.live_params is not candidate
    assert state.live_params == state.known_good
    assert state.pending_params is None
    assert state.consecutive_losses == 0


def test_shadow_window_requires_n_bars_and_pnl() -> None:
    assert not shadow_window_pnl_ok(pnl=0.1, bars=5, required_bars=10, min_pnl=0.0)
    assert shadow_window_pnl_ok(pnl=0.1, bars=10, required_bars=10, min_pnl=0.0)
