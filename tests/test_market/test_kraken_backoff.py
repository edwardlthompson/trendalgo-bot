"""Kraken candle pages back off on rate limits instead of failing the first time (E7)."""

from __future__ import annotations

from datetime import UTC, datetime

import ccxt
import pytest

from trendalgo.market import kraken as kraken_market

SINCE = datetime(2023, 11, 14, 22, 0, tzinfo=UTC)
SINCE_MS = int(SINCE.timestamp() * 1000)


class FlakyKraken:
    """Raises a rate-limit error for the first `failures` calls, then returns one candle."""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def fetch_ohlcv(
        self, pair: str, timeframe: str, since: int | None = None, limit: int | None = None
    ) -> list[list[float]]:
        self.calls += 1
        if self.calls <= self.failures:
            raise ccxt.RateLimitExceeded("slow down")
        return [[float(SINCE_MS), 1.0, 1.0, 1.0, 1.0, 1.0]]


def _use(monkeypatch: pytest.MonkeyPatch, exchange: FlakyKraken) -> list[float]:
    sleeps: list[float] = []
    monkeypatch.setattr(kraken_market.time, "sleep", sleeps.append)
    monkeypatch.setattr(kraken_market, "_client", lambda timeout_ms=10_000: exchange)
    return sleeps


def test_rate_limited_pages_are_retried_with_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    exchange = FlakyKraken(failures=2)
    sleeps = _use(monkeypatch, exchange)
    rows = kraken_market._fetch_ohlcv_rows("BTC", "1h", SINCE, SINCE)
    assert len(rows) == 1
    assert exchange.calls == 3
    assert sleeps == [1.0, 2.0]


def test_a_page_that_stays_rate_limited_gives_up(monkeypatch: pytest.MonkeyPatch) -> None:
    exchange = FlakyKraken(failures=99)
    sleeps = _use(monkeypatch, exchange)
    with pytest.raises(ccxt.RateLimitExceeded):
        kraken_market._fetch_ohlcv_rows("BTC", "1h", SINCE, SINCE)
    assert exchange.calls == 4
    assert sleeps == [1.0, 2.0, 4.0]
