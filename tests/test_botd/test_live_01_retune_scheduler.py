"""LIVE-01: daily UTC retune scheduler on purged rolling window."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trendalgo.botd.retune_scheduler import (
    RetuneCycle,
    clamp_rolling_window,
    due_for_retune,
    pick_verdict,
    run_retune_cycle,
)


def test_clamp_rolling_window_never_full_series() -> None:
    assert clamp_rolling_window(10_000) == 1000
    assert clamp_rolling_window(750) == 750
    assert clamp_rolling_window(100) == 500  # raise to floor when series allows later


def test_due_for_retune_daily_utc_and_tf_floor() -> None:
    now = datetime(2026, 11, 11, 6, 0, tzinfo=UTC)
    last = datetime(2026, 11, 10, 6, 0, tzinfo=UTC)
    assert due_for_retune(now, last, strategy_tf_hours=1.0, scheduled_hour_utc=6)
    assert not due_for_retune(now, last + timedelta(hours=1), strategy_tf_hours=1.0, scheduled_hour_utc=6)
    # 48h TF → floor tf/24 = 2h; daily (24h) still due
    assert due_for_retune(now, last, strategy_tf_hours=48.0, scheduled_hour_utc=6)
    # 720h TF → floor 30h; 24h since last is not enough
    assert not due_for_retune(now, last, strategy_tf_hours=720.0, scheduled_hour_utc=6)
    later = datetime(2026, 11, 12, 6, 0, tzinfo=UTC)  # 48h later, at hour
    assert due_for_retune(later, last, strategy_tf_hours=720.0, scheduled_hour_utc=6)


def test_incumbent_wins_ties() -> None:
    assert pick_verdict(incumbent_net=1.0, candidate_net=1.0) == "no_change"
    assert pick_verdict(incumbent_net=1.0, candidate_net=1.5) == "propose"
    assert pick_verdict(incumbent_net=2.0, candidate_net=1.0) == "no_change"


def test_journal_every_cycle() -> None:
    cycle = run_retune_cycle(
        bar_count=800,
        incumbent_params={"q": 0.5},
        candidate_params={"q": 0.6},
        incumbent_net=1.0,
        candidate_net=1.2,
        purge_bars=4,
        now_utc=datetime(2026, 11, 11, 6, 0, tzinfo=UTC),
    )
    assert isinstance(cycle, RetuneCycle)
    assert cycle.window_bars == 800
    assert cycle.verdict == "propose"
    assert cycle.journal["inputs"]["bar_count"] == 800
    assert cycle.journal["candidates"]
    assert cycle.journal["verdict"] == "propose"
    assert len(cycle.train_indexes) > 0
    assert len(cycle.holdout_indexes) > 0
    # purged: no index overlap
    assert not set(cycle.train_indexes) & set(cycle.holdout_indexes)
