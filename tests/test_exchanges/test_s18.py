"""S18 Phase 1 worldwide native trading tests."""

from __future__ import annotations

from trendalgo.exchanges.pair_normalizer import normalize_pair
from trendalgo.exchanges.registry import (
    list_trading_exchanges,
    list_worldwide_trading_exchanges,
    load_registry,
)
from trendalgo.trading.multi_exchange import route_order


def test_registry_s18_worldwide_phase1() -> None:
    registry = load_registry()
    assert registry.version == 5
    assert registry.worldwide_trading_phase == 1
    trading_ids = {e.id for e in list_trading_exchanges()}
    assert {"binance", "bybit", "okx"}.issubset(trading_ids)
    worldwide = {e.id for e in list_worldwide_trading_exchanges()}
    assert worldwide == {"binance", "bybit", "okx"}


def test_pair_normalization_usdt_quotes() -> None:
    assert normalize_pair("BTC/USD", "binance") == "BTC/USDT"
    assert normalize_pair("ETH/USD", "okx") == "ETH/USDT"
    assert normalize_pair("BTC/USD", "kraken") == "BTC/USD"


def test_worldwide_dry_run_route() -> None:
    result = route_order("bybit", "BTC/USD", "buy", 50.0, dry_run=True)
    assert result["exchange"] == "bybit"
    assert result["pair"] == "BTC/USDT"
    assert result["status"] == "simulated"
    assert result["us_restricted"] is True


def test_worldwide_live_requires_ack(monkeypatch) -> None:
    monkeypatch.delenv("WORLDWIDE_TRADING_ACK", raising=False)
    try:
        route_order("binance", "BTC/USDT", "buy", 10.0, dry_run=False)
        raise AssertionError("expected ack guard")
    except ValueError as exc:
        assert "WORLDWIDE_TRADING_ACK" in str(exc)


def test_runner_status_worldwide_api() -> None:
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trading/runner/status")
    body = resp.json()
    assert body["worldwide_trading_phase"] == 1
    assert "binance" in body["worldwide_exchanges"]
    assert len(body["exchanges"]) == 7
