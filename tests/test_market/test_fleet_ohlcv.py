"""Tests for fleet OHLCV timeframe gating."""

from __future__ import annotations

import trendalgo.market.fleet_ohlcv as fleet_ohlcv


def test_select_tv_timeframes_kraken_1m_floor(monkeypatch) -> None:
    monkeypatch.setattr(
        fleet_ohlcv,
        "list_exchange_fetch_timeframes",
        lambda _ex: ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"),
    )
    gated = fleet_ohlcv.select_tv_timeframes_for_exchange("kraken", min_fetch_timeframe="1m")
    assert gated == ("1", "5", "15", "30", "60", "240", "1D", "1W")
    assert "1S" not in gated
    assert "3" not in gated


def test_select_tv_timeframes_1h_floor_excludes_sub_hour(monkeypatch) -> None:
    monkeypatch.setattr(
        fleet_ohlcv,
        "list_exchange_fetch_timeframes",
        lambda _ex: ("1h", "4h", "1d", "1w"),
    )
    gated = fleet_ohlcv.select_tv_timeframes_for_exchange("kraken", min_fetch_timeframe="1h")
    assert gated == ("60", "240", "1D", "1W")
    assert "1" not in gated


def test_resolve_finest_fetch_timeframe_kraken_30d() -> None:
    tf = fleet_ohlcv.resolve_finest_fetch_timeframe("kraken", 30 * 86_400)
    assert tf == "1h"


def test_min_fetch_seconds_for_30d() -> None:
    sec = fleet_ohlcv.min_fetch_seconds_for_lookback(30 * 86_400)
    assert sec == 3240


def test_resolve_fleet_timeframes_synthetic_uses_all(monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    from datetime import UTC, datetime, timedelta

    from trendalgo.market.service import PriceHistoryService

    market = PriceHistoryService.__new__(PriceHistoryService)
    since = datetime.now(UTC) - timedelta(days=30)
    until = datetime.now(UTC)
    out = fleet_ohlcv.resolve_fleet_timeframes(
        market,
        "kraken",
        "BTC/USD",
        since,
        until,
        None,
    )
    assert "1S" in out
