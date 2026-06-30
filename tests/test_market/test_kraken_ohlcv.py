"""Kraken OHLCV market helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trendalgo.market import kraken as kraken_market
from trendalgo.market.symbols import kraken_ccxt_pair


def test_kraken_pair_known_and_fallback() -> None:
    assert kraken_market.kraken_pair("btc") == "BTC/USD"
    assert kraken_market.kraken_pair("LTC") == kraken_ccxt_pair("LTC")


def test_fetch_ohlcv_maps_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    since = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    until = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    t0 = int(since.timestamp()) * 1000

    class FakeKraken:
        def fetch_ohlcv(self, _pair: str, _tf: str, since: int | None = None, limit: int = 720) -> list[list[float]]:
            del since, limit
            return [[t0, 1.0, 2.0, 0.5, 1.5, 10.0]]

    monkeypatch.setattr(kraken_market, "_client", lambda: FakeKraken())
    points = kraken_market.fetch_ohlcv("BTC", "1h", since, until)
    assert len(points) == 1
    assert points[0].close == 1.5


def test_fetch_closes_returns_price_points(monkeypatch: pytest.MonkeyPatch) -> None:
    since = datetime(2026, 1, 1, tzinfo=UTC)
    until = datetime(2026, 1, 2, tzinfo=UTC)
    t0 = int(since.timestamp()) * 1000

    class FakeKraken:
        def fetch_ohlcv(self, *_args, **_kwargs) -> list[list[float]]:
            return [[t0, 1.0, 2.0, 0.5, 42.0, 10.0]]

    monkeypatch.setattr(kraken_market, "_client", lambda: FakeKraken())
    closes = kraken_market.fetch_closes("ETH", "1d", since, until)
    assert len(closes) == 1
    assert closes[0].close == 42.0
