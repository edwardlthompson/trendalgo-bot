"""Auto-scan interval helpers: wall-clock alignment and freshness (no Qt)."""

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


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _as_local(dt: datetime) -> datetime:
    return _as_utc(dt).astimezone()


def due_at(last: datetime, interval_minutes: int) -> datetime:
    """Relative due time: last completion + interval (UTC-aware)."""
    return _as_utc(last) + timedelta(minutes=clamp_interval_minutes(interval_minutes))


def most_recent_aligned_boundary(
    interval_minutes: int,
    *,
    now: datetime | None = None,
) -> datetime:
    """Latest local wall-clock slot at or before now (UTC-aware return)."""
    minutes = clamp_interval_minutes(interval_minutes)
    local_now = _as_local(now or datetime.now(tz=UTC))
    midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = int((local_now - midnight).total_seconds() // 60)
    slot = (elapsed // minutes) * minutes
    boundary_local = midnight + timedelta(minutes=slot)
    return boundary_local.astimezone(UTC)


def next_aligned_run(interval_minutes: int, *, now: datetime | None = None) -> datetime:
    """Next local wall-clock slot strictly after now (60m = next local :00)."""
    minutes = clamp_interval_minutes(interval_minutes)
    local_now = _as_local(now or datetime.now(tz=UTC))
    boundary = most_recent_aligned_boundary(minutes, now=local_now)
    boundary_local = boundary.astimezone(local_now.tzinfo)
    if local_now > boundary_local:
        nxt = boundary_local + timedelta(minutes=minutes)
    elif local_now == boundary_local:
        nxt = boundary_local + timedelta(minutes=minutes)
    else:
        nxt = boundary_local
    # If we landed exactly on now (second precision), step forward.
    if nxt <= local_now:
        nxt = nxt + timedelta(minutes=minutes)
    return nxt.astimezone(UTC)


def is_stale(
    last: datetime | None,
    interval_minutes: int,
    *,
    now: datetime | None = None,
) -> bool:
    """True when there is no scan, or last finished before the current aligned slot."""
    if last is None:
        return True
    clock = now or datetime.now(tz=UTC)
    boundary = most_recent_aligned_boundary(interval_minutes, now=clock)
    return _as_utc(last) < boundary


def next_run_at(interval_minutes: int, *, now: datetime | None = None) -> datetime:
    """Deprecated relative helper; prefer next_aligned_run for Scanner scheduling."""
    base = now or datetime.now(tz=UTC)
    return _as_utc(base) + timedelta(minutes=clamp_interval_minutes(interval_minutes))


def minutes_until(target: datetime, *, now: datetime | None = None) -> int:
    base = _as_utc(now or datetime.now(tz=UTC))
    end = _as_utc(target)
    seconds = max(0, int((end - base).total_seconds()))
    return max(0, (seconds + 59) // 60)
