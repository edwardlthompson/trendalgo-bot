"""CEX-P1a: smoke + harden generic portfolio sync for 8 non-Kraken venues."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from trendalgo.device.secrets_vault import VaultEntry, memory_vault_for_tests
from trendalgo.exchanges.adapters.fixtures import DRY_RUN_HOLDINGS
from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.base import holdings_from_ccxt_balance
from trendalgo.exchanges.fee_sync import load_seed_config
from trendalgo.exchanges.pair_normalizer import normalize_pair, quote_currency, to_ccxt_pair
from trendalgo.exchanges.private_client import SerializedExchange, set_secret_store
from trendalgo.exchanges.registry import ExchangeEntry, get_entry, list_portfolio_exchanges
from trendalgo.exchanges.sync import sync_all_exchanges
from trendalgo.portfolio.db import PortfolioStore

NON_KRAKEN_IDS = tuple(e.id for e in list_portfolio_exchanges() if e.id != "kraken")


def _non_kraken_entries() -> list[ExchangeEntry]:
    return [e for e in list_portfolio_exchanges() if e.id != "kraken"]


@pytest.fixture
def portfolio_store(tmp_path: Path) -> PortfolioStore:
    return PortfolioStore(tmp_path / "portfolio.db")


def test_non_kraken_portfolio_count() -> None:
    assert len(NON_KRAKEN_IDS) == 8


def test_non_kraken_registry_invariants() -> None:
    _, fee_seeds = load_seed_config()
    for entry in _non_kraken_entries():
        assert entry.portfolio_enabled
        assert entry.ccxt_id
        assert entry.max_private_calls_per_min is not None
        assert entry.min_sync_interval_sec is not None
        assert entry.id in fee_seeds, f"missing fee seed for {entry.id}"
        assert entry.id in DRY_RUN_HOLDINGS, f"missing dry-run fixture for {entry.id}"
        qc = quote_currency(entry)
        assert normalize_pair("BTC/USD", entry.id) == f"BTC/{qc}"
        assert to_ccxt_pair("ETH", entry.id) == f"ETH/{qc}"


@pytest.mark.parametrize("exchange_id", NON_KRAKEN_IDS)
def test_non_kraken_dry_run_sync_smoke(portfolio_store: PortfolioStore, exchange_id: str) -> None:
    result = GenericCcxtPortfolioAdapter(get_entry(exchange_id)).sync_balances(
        portfolio_store, dry_run=True
    )
    assert result["mode"] == "dry-run"
    assert result["exchange"] == exchange_id
    assert result["total_usd"] > 0
    assert result["holdings"] >= 1


def test_non_kraken_staggered_dry_run_sync_smoke(portfolio_store: PortfolioStore) -> None:
    result = sync_all_exchanges(portfolio_store, dry_run=True)
    assert result["exchange_count"] == 9
    for exchange_id in NON_KRAKEN_IDS:
        venue = result[exchange_id]
        assert venue["mode"] == "dry-run"
        assert float(venue["total_usd"]) > 0


class _MockCcxtExchange:
    """Minimal CCXT surface for reconcile + balance pricing tests."""

    def __init__(self, *, quote: str) -> None:
        self._quote = quote

    def nonce(self) -> int:
        return 1_700_000_000_000

    def fetch_balance(self) -> dict[str, Any]:
        return {"total": {"BTC": 0.01, self._quote: 250.0}}

    def fetch_tickers(self) -> dict[str, Any]:
        return {f"BTC/{self._quote}": {"last": 50_000.0}}

    def fetch_open_orders(self, *_a: Any, **_k: Any) -> list[dict[str, Any]]:
        return []

    def fetch_closed_orders(self, *_a: Any, **_k: Any) -> list[dict[str, Any]]:
        return []


@pytest.mark.parametrize("exchange_id", NON_KRAKEN_IDS)
def test_non_kraken_mock_live_sync_with_vault_query_scope(
    portfolio_store: PortfolioStore,
    monkeypatch: pytest.MonkeyPatch,
    exchange_id: str,
) -> None:
    entry = get_entry(exchange_id)
    vault, _mem = memory_vault_for_tests()
    vault.bind_registry()
    vault.write_entry(
        VaultEntry(
            exchange_id=exchange_id,
            api_key="test-key",
            api_secret="x" * 16,
            scope="query",
        )
    )
    set_secret_store(vault)
    inner = _MockCcxtExchange(quote=entry.quote_currency)
    wrapped = SerializedExchange(
        inner,
        exchange_id=entry.id,
        max_private_per_min=entry.max_private_calls_per_min,
    )
    monkeypatch.setattr(GenericCcxtPortfolioAdapter, "_client", lambda self: wrapped)
    result = GenericCcxtPortfolioAdapter(entry).sync_balances(portfolio_store, dry_run=False)
    assert result["mode"] == "live"
    assert result["exchange"] == exchange_id
    # BTC 0.01 @ 50k + 250 quote stable
    assert result["total_usd"] == pytest.approx(750.0, rel=1e-3)
    set_secret_store(None)


def test_holdings_from_ccxt_balance_uses_venue_quote() -> None:
    tickers = {"ETH/USDT": {"last": 3000.0}}
    holdings, total = holdings_from_ccxt_balance(
        {"total": {"ETH": 1.0}},
        tickers,
        quote_currency="USDT",
    )
    assert len(holdings) == 1
    assert holdings[0].value_usd == pytest.approx(3000.0)
    assert total == pytest.approx(3000.0)


def test_vault_keys_keep_dry_run_fixture_path(
    portfolio_store: PortfolioStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vault-only keys must not force a live CCXT call while dry_run=True."""
    exchange_id = "binanceus"
    vault, _mem = memory_vault_for_tests()
    vault.bind_registry()
    vault.write_entry(
        VaultEntry(
            exchange_id=exchange_id,
            api_key="test-key",
            api_secret="y" * 16,
            scope="query",
        )
    )
    set_secret_store(vault)

    def _boom(_self: GenericCcxtPortfolioAdapter) -> Any:
        raise AssertionError("dry-run with vault keys must not call CCXT")

    monkeypatch.setattr(GenericCcxtPortfolioAdapter, "_client", _boom)
    result = GenericCcxtPortfolioAdapter(get_entry(exchange_id)).sync_balances(
        portfolio_store, dry_run=True
    )
    assert result["mode"] == "dry-run"
    set_secret_store(None)
