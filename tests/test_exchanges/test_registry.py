"""S13 exchange registry and adapter tests."""

from __future__ import annotations

from pathlib import Path

from trendalgo.exchanges.adapters.binanceus import BinanceUSAdapter
from trendalgo.exchanges.adapters.kraken import KrakenAdapter
from trendalgo.exchanges.registry import get_entry, list_portfolio_exchanges, load_registry
from trendalgo.exchanges.sync import sync_all_exchanges
from trendalgo.portfolio.arbitrage import detect_arbitrage_opportunities
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.trading.multi_exchange import list_supported_exchanges, route_order


def test_registry_loads_tier_a_exchanges() -> None:
    registry = load_registry()
    assert registry.version == 5
    ids = {e.id for e in list_portfolio_exchanges()}
    assert "kraken" in ids
    assert "binanceus" in ids
    assert "coinbaseadvanced" in ids
    kraken = get_entry("kraken")
    assert kraken.ccxt_id == "kraken"
    assert kraken.us_retail is True
    bus = get_entry("binanceus")
    assert bus.ccxt_id == "binanceus"
    assert bus.env_key == "BINANCEUS_API_KEY"


def test_registry_public_dict() -> None:
    entry = get_entry("binanceus")
    public = entry.to_public_dict()
    assert public["brand"] == "Binance.US"
    assert "env_key" not in public


def test_kraken_adapter_dry_run(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    result = KrakenAdapter().sync_balances(store, dry_run=True)
    assert result["mode"] == "dry-run"
    assert result["exchange"] == "kraken"
    assert result["total_usd"] == 1500.0


def test_binanceus_adapter_dry_run(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    result = BinanceUSAdapter().sync_balances(store, dry_run=True)
    assert result["mode"] == "dry-run"
    assert result["exchange"] == "binanceus"
    assert result["total_usd"] == 1700.0


def test_sync_all_exchanges_registry(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    result = sync_all_exchanges(store, dry_run=True)
    assert result["registry_version"] == 5
    assert result["kraken"]["mode"] == "dry-run"
    assert result["binanceus"]["mode"] == "dry-run"
    assert result["binance"]["exchange"] == "binance"
    assert result["coinbaseadvanced"]["exchange"] == "coinbaseadvanced"


def test_trading_router_supports_tier_b() -> None:
    supported = list_supported_exchanges()
    assert "coinbaseadvanced" in supported
    assert "gemini" in supported
    order = route_order("coinbaseadvanced", "BTC/USD", "buy", 0.01, dry_run=True)
    assert order["exchange"] == "coinbaseadvanced"
    assert order["status"] == "simulated"


def test_trading_router_worldwide_phase1() -> None:
    assert "binance" in list_supported_exchanges()
    order = route_order("binance", "BTC/USD", "buy", 0.01, dry_run=True)
    assert order["pair"] == "BTC/USDT"


def test_arbitrage_uses_binanceus() -> None:
    arb = detect_arbitrage_opportunities(dry_run=True)
    assert arb["count"] >= 1
    assert arb["alerts"][0]["sell_exchange"] in ("kraken", "binanceus")
