"""Call budget and backoff for the public REST path (E7)."""

from __future__ import annotations

import pytest

from trendalgo.market.rate_budget import RateBudget, backoff_seconds, call_with_backoff


class SlowDown(Exception):
    """Stands in for a venue rate-limit error."""


def test_budget_takes_at_most_max_calls_per_window() -> None:
    budget = RateBudget(2, window_s=60.0)
    assert budget.try_acquire(0.0)
    assert budget.try_acquire(1.0)
    assert not budget.try_acquire(2.0)  # window full: nothing taken
    assert not budget.try_acquire(59.0)
    assert budget.try_acquire(60.0)  # the call at t=0 has left the window
    assert not budget.try_acquire(60.5)  # window holds t=1 and t=60
    assert budget.try_acquire(61.0)  # t=1 has left the window


def test_refused_calls_do_not_use_up_the_budget() -> None:
    budget = RateBudget(1, window_s=10.0)
    assert budget.try_acquire(0.0)
    assert not budget.try_acquire(5.0)
    assert budget.try_acquire(10.0)  # only the accepted call at t=0 counted


def test_budget_rejects_nonsense_limits() -> None:
    with pytest.raises(ValueError):
        RateBudget(0)
    with pytest.raises(ValueError):
        RateBudget(3, window_s=0)


def test_backoff_doubles_and_then_caps() -> None:
    assert [backoff_seconds(n, base=1.0, cap=5.0) for n in range(4)] == [1.0, 2.0, 4.0, 5.0]
    assert backoff_seconds(0) == 1.0


def test_rate_limit_errors_are_retried_with_growing_waits() -> None:
    sleeps: list[float] = []
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] <= 2:
            raise SlowDown()
        return "ok"

    assert call_with_backoff(flaky, retry_on=(SlowDown,), sleep=sleeps.append) == "ok"
    assert sleeps == [1.0, 2.0]
    assert attempts["n"] == 3


def test_backoff_gives_up_after_the_last_attempt() -> None:
    sleeps: list[float] = []

    def always() -> str:
        raise SlowDown()

    with pytest.raises(SlowDown):
        call_with_backoff(always, retry_on=(SlowDown,), sleep=sleeps.append, attempts=3)
    assert sleeps == [1.0, 2.0]


def test_other_errors_are_not_retried() -> None:
    sleeps: list[float] = []

    def broken() -> str:
        raise KeyError("bad pair")

    with pytest.raises(KeyError):
        call_with_backoff(broken, retry_on=(SlowDown,), sleep=sleeps.append)
    assert sleeps == []
