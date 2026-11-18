"""Forex session helpers — nearly 24h with weekend gaps (≠ US RTH)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class FxGapSummary:
    unexpected_gaps: int
    weekend_skips: int
    note: str


def is_fx_weekend(day: date) -> bool:
    # FX typically quiet Sat; Sun evening reopen — treat Sat+Sun as expected skips for daily bars.
    return day.weekday() >= 5


def validate_fx_daily_bars(
    bar_dates: list[date],
    *,
    since: date,
    until: date,
) -> FxGapSummary:
    expected: set[date] = set()
    weekend_skips = 0
    cur = since
    while cur <= until:
        if is_fx_weekend(cur):
            weekend_skips += 1
        else:
            expected.add(cur)
        cur += timedelta(days=1)
    got = set(bar_dates) & expected
    missing = expected - got
    note = "ok" if not missing else f"missing_sessions:{len(missing)}"
    return FxGapSummary(
        unexpected_gaps=len(missing),
        weekend_skips=weekend_skips,
        note=note,
    )


def bar_unix_to_et_date(ts: int) -> date:
    return datetime.fromtimestamp(ts, tz=_ET).date()
