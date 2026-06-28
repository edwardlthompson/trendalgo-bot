"""Market history service tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from trendalgo.market.cache import PriceCache
from trendalgo.market.service import PriceHistoryService
from trendalgo.market.types import PricePoint


def test_price_cache_roundtrip(tmp_path: Path) -> None:
    cache = PriceCache(tmp_path / "market.db")
    since = datetime(2026, 1, 1, tzinfo=UTC)
    until = datetime(2026, 1, 3, tzinfo=UTC)
    points = [
        PricePoint(time=int(since.timestamp()), close=40_000.0),
        PricePoint(time=int((since + timedelta(days=1)).timestamp()), close=41_000.0),
        PricePoint(time=int(until.timestamp()), close=42_000.0),
    ]
    cache.upsert("kraken", "BTC", "1d", points)
    loaded = cache.query("kraken", "BTC", "1d", since, until)
    assert len(loaded) == 3
    assert loaded[-1].close == 42_000.0


def test_synthetic_service_offline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    svc = PriceHistoryService(tmp_path / "market.db")
    anchor = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
    since = anchor - timedelta(hours=24)
    closes = svc.get_closes("BTC", "1h", since, anchor)
    assert len(closes) == 25
    assert closes[0].close > 0
