"""Backtest / All-TA timeframe grid (sub-hour + 1h..24h)."""

from __future__ import annotations

import re
from typing import Any

HEARTBEAT_TIMEFRAMES: tuple[str, ...] = tuple(f"{hour}h" for hour in range(1, 25))
SUBHOUR_TIMEFRAMES: tuple[str, ...] = ("1m", "5m", "15m", "30m")
ALL_SCAN_TIMEFRAMES: tuple[str, ...] = SUBHOUR_TIMEFRAMES + HEARTBEAT_TIMEFRAMES
_ALLOWED = frozenset(ALL_SCAN_TIMEFRAMES)

# Sub-hour vs 1h–24h are mutually exclusive bands (different lookbacks).
# Live Kraken OHLC: ≤720 bars → 1m ≈12h. 30d of 1m needs the OHLCVT archive
# (not the REST API; keys do not deepen OHLC).

_MINUTE_TF = re.compile(r"^(\d+)m$")
_HOUR_TF = re.compile(r"^(\d+)h$")


def timeframe_hours(label: str) -> int | None:
    match = _HOUR_TF.fullmatch(str(label).strip().lower())
    if not match:
        return None
    hours = int(match.group(1))
    if 1 <= hours <= 24:
        return hours
    return None


def timeframe_minutes(label: str) -> int | None:
    text = str(label).strip().lower()
    m = _MINUTE_TF.fullmatch(text)
    if m:
        mins = int(m.group(1))
        return mins if mins > 0 else None
    hours = timeframe_hours(text)
    if hours is not None:
        return hours * 60
    if text in ("1d", "daily"):
        return 24 * 60
    return None


def needs_1m_base(timeframes: tuple[str, ...] | list[str]) -> bool:
    for tf in timeframes:
        mins = timeframe_minutes(str(tf))
        if mins is not None and mins < 60:
            return True
    return False


def normalize_timeframes(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        key = str(item).strip().lower()
        if key not in _ALLOWED or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def sort_timeframes(timeframes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    def key(tf: str) -> tuple[int, str]:
        mins = timeframe_minutes(tf)
        return (mins if mins is not None else 10_000, tf)

    return tuple(sorted(timeframes, key=key))


def is_subhour_tf(label: str) -> bool:
    mins = timeframe_minutes(label)
    return mins is not None and mins < 60


def exclusive_scan_timeframes(timeframes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """One band only: sub-hour (~12h) xor 1h–24h (30d). Mixed prefs keep hours."""
    ordered = sort_timeframes(normalize_timeframes(list(timeframes)))
    sub = tuple(tf for tf in ordered if is_subhour_tf(tf))
    hours = tuple(tf for tf in ordered if not is_subhour_tf(tf))
    if sub and hours:
        return hours
    return ordered


def comparable_scan_timeframes(
    timeframes: tuple[str, ...] | list[str],
    *,
    deep_1m: bool = False,
) -> tuple[str, ...]:
    """Exclusive bands unless ``deep_1m`` (rolling 30d or quarterly catch-up)."""
    ordered = sort_timeframes(normalize_timeframes(list(timeframes)))
    if deep_1m:
        return ordered
    return exclusive_scan_timeframes(ordered)
