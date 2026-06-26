"""S14 worldwide portfolio, asset mapper, scheduler tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.asset_mapper import normalize_asset
from trendalgo.exchanges.pair_normalizer import normalize_pair, quote_currency, to_ccxt_pair
from trendalgo.exchanges.registry import get_entry, list_portfolio_exchanges, load_registry
from trendalgo.exchanges.scheduler import sync_portfolio_staggered
from trendalgo.exchanges.sync import sync_all_exchanges
from trendalgo.portfolio.db import PortfolioStore


def test_registry_s14_portfolio_venues() -> None:
    registry = load_registry()
    assert registry.version == 5
    portfolio_ids = {e.id for e in list_portfolio_exchanges()}
    assert portfolio_ids == {
        "kraken",
        "binanceus",
        "coinbaseadvanced",
        "gemini",
        "bitstamp",
        "cryptocom",
        "binance",
        "bybit",
        "okx",
    }
    assert get_entry("coinbaseadvanced").portfolio_enabled is True
    assert get_entry("binance").us_restricted is True
    assert get_entry("binance").trading_enabled is True


def test_normalize_asset_kraken_aliases() -> None:
    assert normalize_asset("ZUSD") == "USD"
    assert normalize_asset("XXBT") == "BTC"


def test_pair_normalizer_us_vs_global() -> None:
    assert to_ccxt_pair("BTC", "kraken") == "BTC/USD"
    assert to_ccxt_pair("BTC", "binance") == "BTC/USDT"
    assert normalize_pair("BTC/USD", "binance") == "BTC/USDT"
    assert quote_currency("gemini") == "USD"


def test_generic_coinbase_gemini_dry_run(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    for exchange_id in ("coinbaseadvanced", "gemini"):
        result = GenericCcxtPortfolioAdapter(get_entry(exchange_id)).sync_balances(
            store, dry_run=True
        )
        assert result["mode"] == "dry-run"
        assert result["exchange"] == exchange_id
        assert result["total_usd"] > 0


def test_sync_all_nine_exchanges(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    result = sync_all_exchanges(store, dry_run=True)
    assert result["registry_version"] == 5
    assert result["staggered"] is True
    assert result["exchange_count"] == 9
    assert result["coinbaseadvanced"]["mode"] == "dry-run"
    assert result["okx"]["mode"] == "dry-run"


def test_scheduler_stagger_calls_sleep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    monkeypatch.setenv("TRENDALGO_SYNC_STAGGER_SEC", "2")
    with patch("trendalgo.exchanges.scheduler.time.sleep") as sleep_mock:
        sync_portfolio_staggered(store, dry_run=True)
        assert sleep_mock.call_count == 8
