"""Wall-clock aligned autoscan schedule and freshness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from trendalgo.device.scanner_schedule import (
    is_stale,
    most_recent_aligned_boundary,
    next_aligned_run,
)


def test_next_aligned_run_60_is_next_local_hour() -> None:
    # Fixed offset so the test is not flaky across machines.
    local = timezone(timedelta(hours=-4))
    now = datetime(2026, 10, 20, 10, 17, 30, tzinfo=local)
    nxt = next_aligned_run(60, now=now)
    assert nxt.astimezone(local) == datetime(2026, 10, 20, 11, 0, 0, tzinfo=local)


def test_next_aligned_run_on_the_hour_steps_forward() -> None:
    local = timezone(timedelta(hours=-4))
    now = datetime(2026, 10, 20, 11, 0, 0, tzinfo=local)
    nxt = next_aligned_run(60, now=now)
    assert nxt.astimezone(local) == datetime(2026, 10, 20, 12, 0, 0, tzinfo=local)


def test_next_aligned_run_120_even_local_hours() -> None:
    local = timezone(timedelta(hours=-4))
    now = datetime(2026, 10, 20, 9, 15, 0, tzinfo=local)
    nxt = next_aligned_run(120, now=now)
    assert nxt.astimezone(local) == datetime(2026, 10, 20, 10, 0, 0, tzinfo=local)


def test_is_stale_when_missed_current_slot() -> None:
    local = timezone(timedelta(hours=-4))
    now = datetime(2026, 10, 20, 10, 5, 0, tzinfo=local)
    last = datetime(2026, 10, 20, 9, 12, 0, tzinfo=local)
    assert is_stale(last, 60, now=now) is True
    fresh = datetime(2026, 10, 20, 10, 1, 0, tzinfo=local)
    assert is_stale(fresh, 60, now=now) is False


def test_is_stale_none_is_stale() -> None:
    assert is_stale(None, 60) is True


def test_most_recent_aligned_boundary_top_of_hour() -> None:
    local = timezone(timedelta(hours=-4))
    now = datetime(2026, 10, 20, 10, 45, 0, tzinfo=local)
    boundary = most_recent_aligned_boundary(60, now=now)
    assert boundary.astimezone(local) == datetime(2026, 10, 20, 10, 0, 0, tzinfo=local)
    assert boundary.astimezone(UTC).tzinfo is UTC
