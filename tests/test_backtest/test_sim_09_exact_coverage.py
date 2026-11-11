"""SIM-09: coverage scored on exact bars (not silent ±2)."""

from __future__ import annotations

from trendalgo.backtest.oracle_pattern_mine import RuleConjunct
from trendalgo.backtest.secret_sauce_lab.label_rules import score_labeled


def test_exact_coverage_ignores_near_miss() -> None:
    feats = [{"x": 0.0} for _ in range(10)]
    feats[5]["x"] = 1.0
    conj = (RuleConjunct(feature="x", op=">=", value=1.0),)
    # Label at 4 — fire at 5 is within ±2 but not exact.
    near = score_labeled(feats, conj, [4], exact_bars=False)
    exact = score_labeled(feats, conj, [4], exact_bars=True)
    assert near > 0
    assert exact < 0
    assert score_labeled(feats, conj, [5], exact_bars=True) > 0
