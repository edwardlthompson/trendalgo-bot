"""TF-P1: Alpaca read-only positions + equity dry-run sync."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.brokers.alpaca_portfolio import AlpacaPortfolioAdapter, sync_alpaca_portfolio
from trendalgo.device.support_matrix import clear_support_matrix_cache, venue_by_id
from trendalgo.portfolio.db import PortfolioStore


def test_alpaca_dry_run_sync(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "p.db")
    result = sync_alpaca_portfolio(store, dry_run=True)
    assert result["mode"] == "dry-run"
    assert result["broker"] == "alpaca"
    assert result["equity_usd"] > 0
    assert result["holdings"] >= 2
    assert any(p["symbol"] == "AAPL" for p in result["positions"])


def test_alpaca_live_without_keys_stays_dry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET", raising=False)
    store = PortfolioStore(tmp_path / "p.db")
    adapter = AlpacaPortfolioAdapter()
    assert not adapter.has_credentials()
    result = adapter.sync_balances(store, dry_run=False)
    assert result["mode"] == "dry-run"


def test_matrix_tradfi_portfolio_partial() -> None:
    clear_support_matrix_cache()
    tradfi = venue_by_id("tradfi")
    assert tradfi is not None
    assert tradfi.portfolio in {"partial", "yes"}
    assert tradfi.status in {"partial", "coming_soon"}
