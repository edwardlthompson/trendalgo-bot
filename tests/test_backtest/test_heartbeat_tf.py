"""Heartbeat / scan TF helpers (exclusive sub-hour vs hour bands)."""

from __future__ import annotations

from trendalgo.backtest import heartbeat_tf as ht


def test_exclusive_scan_timeframes_prefers_hours_when_mixed() -> None:
    assert ht.exclusive_scan_timeframes(["1m", "5m", "1h", "4h"]) == ("1h", "4h")


def test_exclusive_scan_timeframes_keeps_subhour_alone() -> None:
    assert ht.exclusive_scan_timeframes(["5m", "15m"]) == ("5m", "15m")


def test_comparable_exclusive_until_deep_1m_unlocks_mix() -> None:
    raw = ["1m", "1h"]
    assert ht.comparable_scan_timeframes(raw, deep_1m=False) == ("1h",)
    assert ht.comparable_scan_timeframes(raw, deep_1m=True) == ("1m", "1h")


def test_timeframe_hours_rejects_out_of_range() -> None:
    assert ht.timeframe_hours("0h") is None
    assert ht.timeframe_hours("25h") is None
    assert ht.timeframe_hours("1h") == 1


def test_timeframe_minutes_daily_and_invalid() -> None:
    assert ht.timeframe_minutes("1d") == 24 * 60
    assert ht.timeframe_minutes("daily") == 24 * 60
    assert ht.timeframe_minutes("0m") is None
    assert ht.timeframe_minutes("nope") is None


def test_normalize_timeframes_rejects_non_list() -> None:
    assert ht.normalize_timeframes("1h") == []
    assert ht.normalize_timeframes(["1h", "1h", "bogus"]) == ["1h"]


def test_needs_1m_base() -> None:
    assert ht.needs_1m_base(("1h", "4h")) is False
    assert ht.needs_1m_base(("5m", "1h")) is True
    assert ht.needs_1m_base(("1m",)) is True


def test_sort_timeframes_orders_by_minutes() -> None:
    assert ht.sort_timeframes(["4h", "1m", "15m", "1h"]) == ("1m", "15m", "1h", "4h")


def test_is_subhour_tf() -> None:
    assert ht.is_subhour_tf("5m") is True
    assert ht.is_subhour_tf("1h") is False
