"""Self-imposed NASDAQ earnings calendar throttle (no published quota)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

NASDAQ_CACHE_MIN_AGE_S = 6 * 3600
NASDAQ_MIN_INTERVAL_S = 1.0
NASDAQ_MAX_REQ_PER_DAY = 20
NASDAQ_AHEAD_TRADING_DAYS = 5


@dataclass
class NasdaqBudget:
    day: str
    request_count: int

    def remaining(self) -> int:
        return max(0, NASDAQ_MAX_REQ_PER_DAY - self.request_count)


def budget_from_dict(raw: dict[str, Any] | None) -> NasdaqBudget:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if not raw:
        return NasdaqBudget(day=today, request_count=0)
    day = str(raw.get("day") or today)
    count = int(raw.get("request_count") or 0)
    if day != today:
        return NasdaqBudget(day=today, request_count=0)
    return NasdaqBudget(day=day, request_count=count)


def can_refresh(
    *,
    cache_age_s: float | None,
    budget: NasdaqBudget,
    min_age_s: float = NASDAQ_CACHE_MIN_AGE_S,
) -> tuple[bool, str]:
    if cache_age_s is not None and cache_age_s < min_age_s:
        return False, "cache_fresh"
    if budget.remaining() <= 0:
        return False, "daily_cap"
    return True, "ok"


def trading_days_ahead(start: date, *, n: int = NASDAQ_AHEAD_TRADING_DAYS) -> list[date]:
    """Next n weekdays (caller may further skip holidays)."""
    out: list[date] = []
    cur = start
    while len(out) < n:
        if cur.weekday() < 5:
            out.append(cur)
        cur += timedelta(days=1)
    return out
