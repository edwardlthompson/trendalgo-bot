"""TF-P10: NASDAQ earnings throttle + filter."""

from __future__ import annotations

from datetime import date

from trendalgo.device.calendar.nasdaq_quota import (
    NasdaqBudget,
    can_refresh,
    trading_days_ahead,
)
from trendalgo.device.calendar.providers.nasdaq_calendar import filter_universe, rows_to_events


def test_throttle_cache_fresh() -> None:
    ok, reason = can_refresh(
        cache_age_s=60.0, budget=NasdaqBudget(day="2026-03-15", request_count=0)
    )
    assert not ok
    assert reason == "cache_fresh"


def test_throttle_daily_cap() -> None:
    ok, reason = can_refresh(
        cache_age_s=7 * 3600,
        budget=NasdaqBudget(day="2026-03-15", request_count=20),
    )
    assert not ok
    assert reason == "daily_cap"


def test_trading_days_skip_weekend() -> None:
    days = trading_days_ahead(date(2026, 3, 13), n=3)  # Friday
    assert date(2026, 3, 14) not in days
    assert date(2026, 3, 15) not in days


def test_filter_universe() -> None:
    events = rows_to_events(
        [{"symbol": "AAPL", "name": "Apple"}, {"symbol": "ZZZZ", "name": "Nope"}],
        day=date(2026, 3, 10),
    )
    filtered = filter_universe(events, {"AAPL", "MSFT"})
    assert len(filtered) == 1
    assert filtered[0].coins == ("AAPL",)
    assert filtered[0].source == "nasdaq"
