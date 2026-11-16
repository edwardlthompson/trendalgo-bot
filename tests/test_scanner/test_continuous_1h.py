"""Continuous 1h trades gate: drop zero-volume completed hours."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.live_market import has_idle_completed_1h


def _bars(until: datetime, *, volumes: list[float]) -> list[OhlcvPoint]:
    """Build completed hourly bars ending just before ``until``'s hour."""
    end = until.replace(minute=0, second=0, microsecond=0)
    out: list[OhlcvPoint] = []
    for i, vol in enumerate(reversed(volumes), start=1):
        ts = int((end - timedelta(hours=i)).timestamp())
        out.append(OhlcvPoint(time=ts, open=1.0, high=1.0, low=1.0, close=1.0, volume=vol))
    return list(reversed(out))


def test_has_idle_when_zero_volume_hour() -> None:
    until = datetime(2026, 11, 15, 14, 30, tzinfo=UTC)
    vols = [10.0] * 24
    vols[5] = 0.0
    assert has_idle_completed_1h(_bars(until, volumes=vols), until=until, hours=24) is True


def test_no_idle_when_all_hours_traded() -> None:
    until = datetime(2026, 11, 15, 14, 30, tzinfo=UTC)
    vols = [1.5] * 24
    assert has_idle_completed_1h(_bars(until, volumes=vols), until=until, hours=24) is False


def test_missing_bucket_counts_as_idle() -> None:
    until = datetime(2026, 11, 15, 14, 30, tzinfo=UTC)
    # Only 20 hours present → 4 missing → idle.
    vols = [2.0] * 20
    assert has_idle_completed_1h(_bars(until, volumes=vols), until=until, hours=24) is True
