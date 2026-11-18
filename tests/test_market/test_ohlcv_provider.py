"""Unified OHLCV provider wraps CCXT fetch per exchange_id."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from trendalgo.market.ohlcv_provider import PARITY_OHLCV_EXCHANGES, fetch_ohlcv
from trendalgo.market.types import OhlcvPoint


def test_parity_exchange_list_includes_tier_ab() -> None:
    assert "kraken" in PARITY_OHLCV_EXCHANGES
    assert "binanceus" in PARITY_OHLCV_EXCHANGES
    assert "coinbaseadvanced" in PARITY_OHLCV_EXCHANGES
    assert "gemini" in PARITY_OHLCV_EXCHANGES


def test_fetch_ohlcv_passes_exchange_id() -> None:
    point = OhlcvPoint(time=1, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)
    since = datetime(2024, 1, 1, tzinfo=UTC)
    until = datetime(2024, 1, 2, tzinfo=UTC)
    with patch(
        "trendalgo.market.ohlcv_provider.fetch_exchange_ohlcv",
        return_value=[point],
    ) as mocked:
        out = fetch_ohlcv("binanceus", "BTC/USD", "1h", since, until)
    assert out == [point]
    mocked.assert_called_once()
    assert mocked.call_args.args[0] == "binanceus"
