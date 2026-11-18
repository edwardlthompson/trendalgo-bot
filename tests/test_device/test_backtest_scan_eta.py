"""Unit tests for adaptive Backtest scan ETA helpers."""

from __future__ import annotations

from trendalgo.device.backtest_scan_eta import (
    append_log_line,
    format_pace,
    format_remaining,
    prior_seconds,
    progress_pct,
    remaining_seconds,
)
from trendalgo.device.scan_time_history import ScanTimeHistory


def test_remaining_uses_prior_before_live_pace() -> None:
    snap = remaining_seconds(elapsed_s=0.0, done=0, total=100, prior_s=50.0)
    assert snap.remaining_s == 50.0
    assert snap.pace_s is None
    assert snap.live_s is None


def test_remaining_blends_live_and_prior() -> None:
    # elapsed 20s for 10 done of 100 → pace 2s → live remain 180; prior_remain=45
    snap = remaining_seconds(elapsed_s=20.0, done=10, total=100, prior_s=50.0)
    assert snap.pace_s == 2.0
    assert snap.live_s == 180.0
    assert snap.remaining_s is not None
    # 0.7*180 + 0.3*45 = 126 + 13.5 = 139.5
    assert abs(snap.remaining_s - 139.5) < 0.01


def test_format_remaining_and_pace() -> None:
    assert format_remaining(None) == "—"
    assert "s" in format_remaining(12)
    assert format_pace(None) == ""
    assert "step" in format_pace(2.5)


def test_progress_pct_caps_until_ready() -> None:
    assert progress_pct(done=100, total=100, worker_ready=False) == 99
    assert progress_pct(done=100, total=100, worker_ready=True) == 100
    assert progress_pct(done=0, total=50, worker_ready=False) == 0


def test_append_log_line_dedupes_and_caps() -> None:
    lines = append_log_line([], "hello")
    lines = append_log_line(lines, "hello")
    assert lines == ["hello"]
    lines = append_log_line(lines, "next")
    assert lines == ["hello", "next"]
    many = []
    for i in range(250):
        many = append_log_line(many, f"line-{i}", soft_cap=200)
    assert len(many) == 200
    assert many[0] == "line-50"


def test_prior_seconds_from_history() -> None:
    hist = ScanTimeHistory(mean_load_1h_s=2.0, mean_per_strat_tf_s=0.1)
    assert prior_seconds(hist, n_strategies=10, n_timeframes=2, had_subhour=False) >= 0.5
