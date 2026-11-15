"""CEX-P1b: Coinbase Advanced + Gemini use dedicated portfolio adapters."""

from __future__ import annotations

from pathlib import Path

from trendalgo.exchanges.adapters.coinbaseadvanced import CoinbaseAdvancedAdapter
from trendalgo.exchanges.adapters.factory import portfolio_adapter_for
from trendalgo.exchanges.adapters.gemini import GeminiAdapter
from trendalgo.exchanges.sync import get_portfolio_adapter
from trendalgo.portfolio.db import PortfolioStore


def test_factory_returns_dedicated_types() -> None:
    assert isinstance(portfolio_adapter_for("coinbaseadvanced"), CoinbaseAdvancedAdapter)
    assert isinstance(portfolio_adapter_for("gemini"), GeminiAdapter)
    assert isinstance(get_portfolio_adapter("coinbaseadvanced"), CoinbaseAdvancedAdapter)


def test_coinbase_aliases_include_usdc() -> None:
    adapter = CoinbaseAdvancedAdapter()
    assert "USDC" in adapter._usd_aliases()
    assert "USD" in adapter._usd_aliases()


def test_gemini_aliases_include_gusd() -> None:
    adapter = GeminiAdapter()
    assert "GUSD" in adapter._usd_aliases()


def test_dedicated_dry_run_sync(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "p.db")
    for eid in ("coinbaseadvanced", "gemini"):
        result = get_portfolio_adapter(eid).sync_balances(store, dry_run=True)
        assert result["mode"] == "dry-run"
        assert result["exchange"] == eid
        assert result["holdings"] >= 1
