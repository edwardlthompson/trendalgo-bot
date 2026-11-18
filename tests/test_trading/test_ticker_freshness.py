"""RISK-07: ticker age is directional; small clock skew is allowed."""

from __future__ import annotations

import pytest

from trendalgo.trading.sizing import OrderSizingError, check_ticker_fresh


def test_two_seconds_fast_passes() -> None:
    now = 1_000_000.0
    check_ticker_fresh(now + 2_000, now, max_age_s=15.0)


def test_twenty_nine_seconds_fast_fails() -> None:
    now = 1_000_000.0
    with pytest.raises(OrderSizingError, match="clock"):
        check_ticker_fresh(now + 29_000, now, max_age_s=15.0)


def test_twenty_nine_seconds_stale_fails_at_fifteen() -> None:
    now = 1_000_000.0
    with pytest.raises(OrderSizingError, match="stale|age"):
        check_ticker_fresh(now - 29_000, now, max_age_s=15.0)
