"""Backtest-tab heartbeat timeframe grid (1h..24h)."""

from __future__ import annotations

import re

HEARTBEAT_TIMEFRAMES: tuple[str, ...] = tuple(f"{hour}h" for hour in range(1, 25))


def timeframe_hours(label: str) -> int | None:
    match = re.fullmatch(r"(\d+)h", str(label).strip().lower())
    if not match:
        return None
    hours = int(match.group(1))
    if 1 <= hours <= 24:
        return hours
    return None


def sort_timeframes(timeframes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    def key(tf: str) -> tuple[int, str]:
        hours = timeframe_hours(tf)
        return (hours if hours is not None else 999, tf)

    return tuple(sorted(timeframes, key=key))
