"""LIVE-05: Study never presents re-fit Net% as live track record."""

from __future__ import annotations

from trendalgo.botd.study_honesty import (
    StudyNetView,
    format_param_diff,
    separate_study_nets,
)


def test_separate_refit_from_live() -> None:
    view = separate_study_nets(refit_net_pct=12.5, live_net_pct=3.1)
    assert isinstance(view, StudyNetView)
    assert "12.50" in view.refit_label
    assert "3.10" in view.live_label
    assert view.refit_label != view.live_label
    assert "re-fit" in view.refit_label.lower() or "refit" in view.refit_label.lower()
    assert "live" in view.live_label.lower()
    # Combined banner must not imply refit is track record
    assert "not a track record" in view.disclaimer.lower()


def test_diff_evidence() -> None:
    text = format_param_diff(
        old={"q": 0.5, "stop": 2.0},
        new={"q": 0.6, "stop": 2.0},
        regime_axis="structural",
        holdout_evidence={"incumbent": 1.0, "candidate": 1.4, "margin": 0.01},
    )
    assert "q: 0.5 → 0.6" in text
    assert "structural" in text
    assert "1.4" in text
