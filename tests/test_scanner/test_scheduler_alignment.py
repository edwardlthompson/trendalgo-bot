"""Verify scanner scheduler aligns 60m runs to the top of the hour (:00:00)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trendalgo.scanner.scheduler import compute_start_date


def test_compute_start_date_60m_aligns_to_top_of_hour() -> None:
    for hour, minute, second in [(14, 23, 41), (14, 0, 0), (23, 59, 59), (0, 1, 0)]:
        now = datetime(2026, 11, 24, hour, minute, second, tzinfo=UTC)
        start = compute_start_date(60, now=now)
        local_start = start.astimezone()
        assert local_start.minute == 0
        assert local_start.second == 0
        assert local_start.microsecond == 0
        assert start > now
        assert start - now <= timedelta(minutes=60)
