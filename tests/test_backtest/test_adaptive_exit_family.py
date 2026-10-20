"""Phase 1b — adaptive_exit family seeds + soft budgets."""

from __future__ import annotations

from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import FAMILIES, _family_weights


def test_adaptive_exit_in_families() -> None:
    assert "adaptive_exit" in FAMILIES


def test_adaptive_exit_fat_on_uptrend_skim_on_down() -> None:
    up = _family_weights("trending", "low", "up", False, True)
    down = _family_weights("trending", "low", "down", False, True)
    assert up["adaptive_exit"] >= 0.45
    assert down["adaptive_exit"] <= 0.2
    assert down["dip_uptrend"] <= 0.1


def test_adaptive_exit_seeds_have_multi_conjunct_exits() -> None:
    weights = {k: 0.15 for k in FAMILIES}
    weights["adaptive_exit"] = 1.0
    pairs = seeds_for_weights("GEN_SECRET_1", weights, volume_ok=True)
    adaptive = [(e, x) for e, x, f in pairs if f == "adaptive_exit"]
    assert len(adaptive) >= 4
    # At least one exit uses two conjuncts (peak + oscillator / structure).
    assert any(len(x.conjuncts) >= 2 for _e, x in adaptive)
