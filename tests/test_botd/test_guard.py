"""W-PORT: the fixed-window rate limit that the host API applies per route."""

from __future__ import annotations

import pytest

from trendalgo.botd.guard import FixedWindowLimiter


def test_a_limiter_allows_up_to_its_limit_then_refuses_that_key() -> None:
    limiter = FixedWindowLimiter(limit=2, window_s=60)
    assert limiter.allow("/api/v1/plan", 100) is True
    assert limiter.allow("/api/v1/plan", 100) is True
    assert limiter.allow("/api/v1/plan", 100) is False
    assert limiter.allow("/api/v1/events", 100) is True


def test_a_new_window_resets_the_count() -> None:
    limiter = FixedWindowLimiter(limit=1, window_s=60)
    assert limiter.allow("/api/v1/status", 100) is True
    assert limiter.allow("/api/v1/status", 100) is False
    assert limiter.allow("/api/v1/status", 120) is True


def test_old_windows_are_dropped_so_memory_stays_bounded() -> None:
    limiter = FixedWindowLimiter(limit=5, window_s=60)
    for window in range(10):
        limiter.allow("/api/v1/status", window * 60)
    assert len(limiter._counts) == 1


def test_a_limit_and_window_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        FixedWindowLimiter(limit=0)
    with pytest.raises(ValueError, match="positive"):
        FixedWindowLimiter(window_s=0)
