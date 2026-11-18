"""LIVE-04: regime flip actions before re-fit; one-bar blip no re-fit."""

from __future__ import annotations

from trendalgo.botd.regime_actions import RegimeActionState, on_regime_observation


def test_one_bar_blip_size_cut_no_refit() -> None:
    state = RegimeActionState(regime="trend_up", size_mult=1.0)
    state, action = on_regime_observation(state, regime="choppy", stable_bars_required=3)
    assert action.kind == "size_cut"
    assert action.allow_refit is False
    assert state.size_mult < 1.0
    # blip ends — back to prior
    state, action2 = on_regime_observation(state, regime="trend_up", stable_bars_required=3)
    assert action2.kind == "restore"
    assert action2.allow_refit is False


def test_sustained_flip_escalates_to_refit() -> None:
    state = RegimeActionState(regime="trend_up", size_mult=1.0)
    for _ in range(2):
        state, action = on_regime_observation(state, regime="choppy", stable_bars_required=3)
        assert action.allow_refit is False
    state, action = on_regime_observation(state, regime="choppy", stable_bars_required=3)
    assert action.kind in {"tighten", "cash", "refit_ready"}
    assert action.allow_refit is True
    assert state.regime == "choppy"
