"""Candle reads for the bots: one fetch per pair and timeframe per TTL, inside one call budget (E7).

Every bot reads candles through one CandleFeed. A series fetched within the TTL is served from
memory and costs no call. Any other read takes a slot in the shared RateBudget first. When the
budget is spent the read fails with BudgetExhausted, so a bot never silently trades on old candles.
Backoff on rate-limit errors happens inside the fetch (see trendalgo.market.kraken).
"""

from __future__ import annotations

from collections.abc import Callable

from trendalgo.market.rate_budget import RateBudget

Series = list[list[float]]


class BudgetExhausted(RuntimeError):
    """The shared call budget is spent for now. Retry after the window slides."""


class CandleFeed:
    """Shared candle reads for every bot, bounded by one call budget."""

    def __init__(
        self,
        fetch: Callable[[str, str], Series],
        *,
        budget: RateBudget,
        ttl_s: float,
        clock: Callable[[], float],
    ) -> None:
        self._fetch = fetch
        self._budget = budget
        self._ttl_s = ttl_s
        self._clock = clock
        self._series: dict[tuple[str, str], tuple[float, Series]] = {}
        self.network_calls = 0

    def get(self, pair: str, timeframe: str) -> Series:
        key = (pair, timeframe)
        now = self._clock()
        cached = self._series.get(key)
        if cached is not None and now - cached[0] < self._ttl_s:
            return cached[1]
        if not self._budget.try_acquire(now):
            raise BudgetExhausted(f"call budget spent; {pair} {timeframe} not fetched")
        self.network_calls += 1
        rows = self._fetch(pair, timeframe)
        self._series[key] = (now, rows)
        return rows
