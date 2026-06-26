"""S17 Bitstamp + Crypto.com portfolio and CM-6 load test."""

from __future__ import annotations

from pathlib import Path

from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.load_test import run_load_test
from trendalgo.exchanges.registry import get_entry, list_portfolio_exchanges, load_registry
from trendalgo.exchanges.sync import sync_all_exchanges
from trendalgo.portfolio.db import PortfolioStore


def test_registry_s17_tier_b_venues() -> None:
    registry = load_registry()
    assert registry.version == 6
    portfolio_ids = {e.id for e in list_portfolio_exchanges()}
    assert "bitstamp" in portfolio_ids
    assert "cryptocom" in portfolio_ids
    assert len(portfolio_ids) == 9
    bitstamp = get_entry("bitstamp")
    assert bitstamp.ccxt_id == "bitstamp"
    assert bitstamp.trading_enabled is True
    cryptocom = get_entry("cryptocom")
    assert cryptocom.ccxt_id == "cryptocom"


def test_bitstamp_cryptocom_dry_run(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    for exchange_id in ("bitstamp", "cryptocom"):
        result = GenericCcxtPortfolioAdapter(get_entry(exchange_id)).sync_balances(
            store, dry_run=True
        )
        assert result["mode"] == "dry-run"
        assert result["total_usd"] > 0


def test_sync_all_nine_exchanges(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    result = sync_all_exchanges(store, dry_run=True)
    assert result["registry_version"] == 6
    assert result["exchange_count"] == 9
    assert result["bitstamp"]["mode"] == "dry-run"
    assert result["cryptocom"]["mode"] == "dry-run"
    assert float(result["elapsed_sec"]) < 30.0


def test_portfolio_load_test() -> None:
    report = run_load_test()
    assert report["ok"] is True
    assert int(report["exchange_count"]) >= 9
