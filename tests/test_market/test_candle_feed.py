"""Candle reads for many bots: one fetch per pair and timeframe per TTL, inside one budget (E7)."""

from __future__ import annotations

import pytest

from trendalgo.market.candle_feed import BudgetExhausted, CandleFeed
from trendalgo.market.rate_budget import RateBudget

PAIRS = ("BTC/USD", "ETH/USD", "SOL/USD")


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Venue:
    """Stands in for the REST call. Records the clock reading of every call."""

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock
        self.calls: list[float] = []

    def __call__(self, pair: str, timeframe: str) -> list[list[float]]:
        self.calls.append(self._clock.now)
        return [[self._clock.now, 1.0, 1.0, 1.0, 1.0, 1.0]]


def _feed(clock: FakeClock, venue: Venue, *, max_calls: int = 6, ttl_s: float = 60.0) -> CandleFeed:
    return CandleFeed(venue, budget=RateBudget(max_calls, 60.0), ttl_s=ttl_s, clock=clock)


def test_five_bots_on_three_pairs_stay_inside_the_call_budget() -> None:
    clock = FakeClock()
    venue = Venue(clock)
    feed = _feed(clock, venue)
    for step in range(0, 600, 5):  # every 5 s for ten minutes
        clock.now = float(step)
        for _bot in range(5):
            for pair in PAIRS:
                feed.get(pair, "1h")
    assert feed.network_calls == 30  # one fetch per pair per minute
    assert len(venue.calls) == 30
    busiest = max(sum(1 for t in venue.calls if start <= t < start + 60.0) for start in venue.calls)
    assert busiest <= 6


def test_the_budget_refuses_calls_past_the_limit_instead_of_hammering_the_venue() -> None:
    clock = FakeClock()
    venue = Venue(clock)
    feed = _feed(clock, venue, max_calls=6, ttl_s=0.0)  # no cache: every read needs a call
    served = 0
    refused = 0
    for _bot in range(5):
        for pair in PAIRS:
            try:
                feed.get(pair, "1h")
                served += 1
            except BudgetExhausted:
                refused += 1
    assert (served, refused) == (6, 9)
    assert len(venue.calls) == 6


def test_a_cached_series_costs_no_call_within_the_ttl() -> None:
    clock = FakeClock()
    venue = Venue(clock)
    feed = _feed(clock, venue, max_calls=1)
    first = feed.get("BTC/USD", "1h")
    clock.now = 59.0
    assert feed.get("BTC/USD", "1h") is first
    assert feed.network_calls == 1


def test_the_ttl_expires_a_series_and_the_next_read_refetches() -> None:
    clock = FakeClock()
    venue = Venue(clock)
    feed = _feed(clock, venue)
    feed.get("BTC/USD", "1h")
    clock.now = 60.0
    feed.get("BTC/USD", "1h")
    assert feed.network_calls == 2


def test_each_timeframe_is_its_own_series() -> None:
    clock = FakeClock()
    venue = Venue(clock)
    feed = _feed(clock, venue)
    feed.get("BTC/USD", "1h")
    feed.get("BTC/USD", "1d")
    assert feed.network_calls == 2


def test_a_spent_budget_recovers_when_the_window_slides() -> None:
    clock = FakeClock()
    venue = Venue(clock)
    feed = _feed(clock, venue, max_calls=1, ttl_s=10.0)
    feed.get("BTC/USD", "1h")  # t=0: the only slot in the window
    clock.now = 20.0  # TTL over, window still holds t=0
    with pytest.raises(BudgetExhausted):
        feed.get("BTC/USD", "1h")
    clock.now = 60.0  # t=0 has left the window
    assert feed.get("BTC/USD", "1h")
    assert feed.network_calls == 2
