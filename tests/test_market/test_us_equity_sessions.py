"""TF-P6: US equity session / gap validation."""

from __future__ import annotations

from datetime import date

from trendalgo.market.us_equity_sessions import (
    expected_1d_sessions,
    is_rth_session_day,
    validate_daily_bars,
)


def test_weekend_not_session() -> None:
    assert not is_rth_session_day(date(2026, 3, 14))  # Saturday
    assert not is_rth_session_day(date(2026, 3, 15))  # Sunday


def test_holiday_not_session() -> None:
    assert not is_rth_session_day(date(2026, 1, 1))


def test_weekend_gap_ok() -> None:
    # Fri + Mon present; weekend skipped — no unexpected gaps.
    summary = validate_daily_bars(
        [date(2026, 3, 13), date(2026, 3, 16)],
        since=date(2026, 3, 13),
        until=date(2026, 3, 16),
    )
    assert summary.unexpected_gaps == 0
    assert summary.expected_skips >= 2
    assert summary.note == "ok"


def test_midweek_hole_flagged() -> None:
    # Mon + Wed; Tuesday missing.
    summary = validate_daily_bars(
        [date(2026, 3, 9), date(2026, 3, 11)],
        since=date(2026, 3, 9),
        until=date(2026, 3, 11),
    )
    assert summary.unexpected_gaps == 1
    assert "missing" in summary.note


def test_expected_sessions_skips_weekend() -> None:
    days = expected_1d_sessions(date(2026, 3, 13), date(2026, 3, 16))
    assert date(2026, 3, 14) not in days
    assert date(2026, 3, 15) not in days
