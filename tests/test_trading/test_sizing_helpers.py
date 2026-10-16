"""E1: pure order-sizing helpers."""

from __future__ import annotations

import math

import pytest

from trendalgo.trading.sizing import (
    OrderSizingError,
    base_amount_from_usd,
    check_exchange_minimums,
    check_ticker_fresh,
)


def test_base_amount_divides_usd_by_price() -> None:
    assert base_amount_from_usd(25.0, 50_000.0) == pytest.approx(0.0005)


@pytest.mark.parametrize("price", [0.0, -1.0, math.nan, math.inf])
def test_unusable_price_is_rejected(price: float) -> None:
    with pytest.raises(OrderSizingError, match="reference price"):
        base_amount_from_usd(25.0, price)


@pytest.mark.parametrize("amount_usd", [0.0, -5.0, math.nan])
def test_unusable_size_is_rejected(amount_usd: float) -> None:
    with pytest.raises(OrderSizingError, match="positive USD amount"):
        base_amount_from_usd(amount_usd, 50_000.0)


def test_no_published_limits_means_no_check() -> None:
    check_exchange_minimums(0.0005, 50_000.0, min_amount=None, min_cost=None)


def test_minimum_amount_is_enforced() -> None:
    with pytest.raises(OrderSizingError, match="below the exchange minimum of 0.0001"):
        check_exchange_minimums(0.00002, 50_000.0, min_amount=0.0001, min_cost=None)


def test_minimum_cost_is_enforced() -> None:
    with pytest.raises(OrderSizingError, match="minimum cost of 5.0"):
        check_exchange_minimums(0.00004, 50_000.0, min_amount=None, min_cost=5.0)


def test_size_that_rounds_to_zero_is_rejected() -> None:
    with pytest.raises(OrderSizingError, match="rounds to zero"):
        check_exchange_minimums(0.0, 50_000.0, min_amount=None, min_cost=None)


def test_fresh_ticker_passes() -> None:
    check_ticker_fresh(1_000_000 - 2_000, 1_000_000)


def test_ticker_at_the_limit_passes() -> None:
    check_ticker_fresh(1_000_000 - 30_000, 1_000_000)


def test_ticker_older_than_limit_is_rejected() -> None:
    with pytest.raises(OrderSizingError, match="from the local clock"):
        check_ticker_fresh(1_000_000 - 31_000, 1_000_000)


def test_ticker_from_the_future_beyond_limit_is_rejected() -> None:
    with pytest.raises(OrderSizingError, match="from the local clock"):
        check_ticker_fresh(1_000_000 + 31_000, 1_000_000)


def test_ticker_without_timestamp_is_rejected() -> None:
    with pytest.raises(OrderSizingError, match="no timestamp"):
        check_ticker_fresh(None, 1_000_000)
