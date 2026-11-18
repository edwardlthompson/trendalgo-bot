"""US equity RTH / holiday session helpers and gap validation (TradFi ≠ crypto continuity)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")

# Fixed US market holidays (observed) — extend annually as needed.
_HOLIDAYS: frozenset[date] = frozenset(
    {
        date(2024, 1, 1),
        date(2024, 1, 15),
        date(2024, 2, 19),
        date(2024, 3, 29),
        date(2024, 5, 27),
        date(2024, 6, 19),
        date(2024, 7, 4),
        date(2024, 9, 2),
        date(2024, 11, 28),
        date(2024, 12, 25),
        date(2025, 1, 1),
        date(2025, 1, 20),
        date(2025, 2, 17),
        date(2025, 4, 18),
        date(2025, 5, 26),
        date(2025, 6, 19),
        date(2025, 7, 4),
        date(2025, 9, 1),
        date(2025, 11, 27),
        date(2025, 12, 25),
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 4, 3),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 3),
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
    }
)


@dataclass(frozen=True)
class GapSummary:
    unexpected_gaps: int
    expected_skips: int
    note: str


def is_us_equity_holiday(day: date) -> bool:
    return day in _HOLIDAYS


def is_rth_session_day(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    return not is_us_equity_holiday(day)


def expected_1d_sessions(since: date, until: date) -> list[date]:
    out: list[date] = []
    cur = since
    while cur <= until:
        if is_rth_session_day(cur):
            out.append(cur)
        cur += timedelta(days=1)
    return out


def validate_daily_bars(
    bar_dates: list[date],
    *,
    since: date,
    until: date,
) -> GapSummary:
    """Flag mid-week holes; weekends/holidays are expected skips."""
    expected = set(expected_1d_sessions(since, until))
    got = {d for d in bar_dates if d in expected}
    missing = sorted(expected - got)
    # Extra bars on closed days count as noise but not unexpected gaps.
    unexpected = len(missing)
    expected_skips = 0
    cur = since
    while cur <= until:
        if not is_rth_session_day(cur):
            expected_skips += 1
        cur += timedelta(days=1)
    if unexpected == 0:
        note = "ok"
    else:
        note = f"missing_sessions:{unexpected}"
    return GapSummary(unexpected_gaps=unexpected, expected_skips=expected_skips, note=note)


def bar_unix_to_et_date(ts: int) -> date:
    return datetime.fromtimestamp(ts, tz=_ET).date()
