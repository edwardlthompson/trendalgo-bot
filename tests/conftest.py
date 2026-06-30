"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def synthetic_market_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests must not call live Kraken OHLCV."""
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    from trendalgo.market.service import reset_price_history_service

    reset_price_history_service()


@pytest.fixture(autouse=True)
def isolate_portfolio_fixtures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests use simple dry-run fixtures, not the stress portfolio."""
    monkeypatch.setenv("TRENDALGO_STRESS_PORTFOLIO", "0")


@pytest.fixture(autouse=True)
def zero_sync_stagger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Portfolio sync tests must not sleep between exchanges."""
    monkeypatch.setenv("TRENDALGO_SYNC_STAGGER_SEC", "0")
    from trendalgo.exchanges.registry import load_registry

    load_registry.cache_clear()


@pytest.fixture(autouse=True)
def isolate_exchange_fee_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests use seeded fees only — no live CCXT pull on API startup."""
    monkeypatch.setenv("TRENDALGO_FEE_SYNC_ON_START", "0")
    from trendalgo.exchanges import fees
    from trendalgo.exchanges.fee_store import reset_fee_store

    reset_fee_store()
    fees.clear_fee_cache()
    yield
    reset_fee_store()
    fees.clear_fee_cache()


@pytest.fixture(autouse=True)
def fast_fee_fetch_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cap live fee-page fetches so accidental sync calls cannot stall CI."""
    monkeypatch.setenv("TRENDALGO_FEE_FETCH_TIMEOUT", "3")
