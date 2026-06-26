"""S19 Phase 2 trading + multi-venue arbitrage tests."""

from __future__ import annotations

from trendalgo.exchanges.registry import (
    get_entry,
    list_trading_exchanges,
    list_worldwide_trading_exchanges,
    load_registry,
)
from trendalgo.portfolio.arbitrage import detect_arbitrage_opportunities
from trendalgo.trading.multi_exchange import list_supported_exchanges, route_order


def test_registry_s19_phase2_tier_b_trading() -> None:
    registry = load_registry()
    assert registry.version == 6
    assert registry.worldwide_trading_phase == 2
    trading_ids = {entry.id for entry in list_trading_exchanges()}
    assert {"bitstamp", "cryptocom"}.issubset(trading_ids)
    assert len(trading_ids) == 9
    assert get_entry("bitstamp").trading_enabled is True
    assert get_entry("cryptocom").trading_enabled is True
    worldwide = {entry.id for entry in list_worldwide_trading_exchanges()}
    assert worldwide == {"binance", "bybit", "okx"}


def test_tier_b_dry_run_route() -> None:
    for exchange_id in ("bitstamp", "cryptocom"):
        result = route_order(exchange_id, "BTC/USD", "buy", 25.0, dry_run=True)
        assert result["exchange"] == exchange_id
        assert result["status"] == "simulated"


def test_multi_venue_arbitrage_registry_driven() -> None:
    arb = detect_arbitrage_opportunities(dry_run=True)
    assert arb["auto_trade"] is False
    assert arb["count"] >= 1
    assert len(arb["venues"]) == 9
    alert = arb["alerts"][0]
    assert alert["informational_only"] is True
    assert alert["venues_compared"] >= 2
    assert alert["buy_exchange"] in arb["venues"]
    assert alert["sell_exchange"] in arb["venues"]
    assert alert["prices"][alert["buy_exchange"]] < alert["prices"][alert["sell_exchange"]]


def test_trading_arbitrage_signals_api() -> None:
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trading/arbitrage/signals")
    body = resp.json()
    assert resp.status_code == 200
    assert body["trading_lane"] is True
    assert body["auto_trade"] is False
    assert body["count"] >= 1
    assert len(body["venues"]) == len(list_supported_exchanges())


def test_runner_status_phase2_api() -> None:
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trading/runner/status")
    body = resp.json()
    assert body["worldwide_trading_phase"] == 2
    assert "bitstamp" in body["exchanges"]
    assert "cryptocom" in body["exchanges"]
    assert len(body["exchanges"]) == 9
