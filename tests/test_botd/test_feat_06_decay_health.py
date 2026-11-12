"""FEAT-06: strategy decay health score + de-risk (shares SIM-11)."""

from __future__ import annotations

from trendalgo.botd.decay_monitor import derisk_action, evaluate_health, health_score


def test_health_score_tracks_live_vs_fit() -> None:
    assert health_score(live_net_pct=10.0, fitted_net_pct=10.0, trades=30) == 1.0
    assert health_score(live_net_pct=5.0, fitted_net_pct=10.0, trades=30) == 0.5
    assert health_score(live_net_pct=5.0, fitted_net_pct=10.0, trades=5) == 1.0


def test_derisk_thresholds() -> None:
    assert derisk_action(0.8) == "none"
    assert derisk_action(0.5) == "reduce_size"
    assert derisk_action(0.2) == "pause"


def test_evaluate_health_pauses_severe_decay() -> None:
    health = evaluate_health(bot_id=3, live_net_pct=1.0, fitted_net_pct=10.0, trades=40)
    assert health.score == 0.1
    assert health.action == "pause"
