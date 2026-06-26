"""S16+ trading adapter tests."""

from __future__ import annotations

from trendalgo.trading.multi_exchange import list_supported_exchanges, route_order
from trendalgo.trading.runner.adapters.registry import get_trading_adapter


def test_us_trading_exchanges_enabled() -> None:
    supported = list_supported_exchanges()
    for ex in ("kraken", "binanceus", "coinbaseadvanced", "gemini"):
        assert ex in supported


def test_worldwide_phase1_trading_enabled() -> None:
    supported = list_supported_exchanges()
    for ex in ("binance", "bybit", "okx"):
        assert ex in supported
    assert len(supported) == 7


def test_coinbase_adapter_simulates_order() -> None:
    adapter = get_trading_adapter("coinbaseadvanced")
    order = adapter.simulate_order("BTC/USD", "buy", 50.0, 50000.0)
    assert order["exchange"] == "coinbaseadvanced"
    assert order["mode"] == "dry_run"
    assert order["order_id"].startswith("dry-coinbaseadvanced-")


def test_gemini_route_order() -> None:
    result = route_order("gemini", "ETH/USD", "buy", 25.0, dry_run=True)
    assert result["exchange"] == "gemini"
    assert result["status"] == "simulated"


def test_okx_route_normalizes_pair() -> None:
    result = route_order("okx", "BTC/USD", "buy", 25.0, dry_run=True)
    assert result["pair"] == "BTC/USDT"
    assert result["exchange"] == "okx"
