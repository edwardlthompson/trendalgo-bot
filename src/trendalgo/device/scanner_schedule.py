"""Auto-scan interval helpers (no Qt)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

MIN_INTERVAL = 60
MAX_INTERVAL = 1440


def clamp_interval_minutes(raw: int | float | None, default: int = MIN_INTERVAL) -> int:
    try:
        value = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        value = default
    return max(MIN_INTERVAL, min(MAX_INTERVAL, value))


def next_run_at(interval_minutes: int, *, now: datetime | None = None) -> datetime:
    base = now or datetime.now(tz=UTC)
    return base + timedelta(minutes=clamp_interval_minutes(interval_minutes))


def minutes_until(target: datetime, *, now: datetime | None = None) -> int:
    base = now or datetime.now(tz=UTC)
    if target.tzinfo is None:
        target = target.replace(tzinfo=UTC)
    if base.tzinfo is None:
        base = base.replace(tzinfo=UTC)
    seconds = max(0, int((target - base).total_seconds()))
    return max(0, (seconds + 59) // 60)
