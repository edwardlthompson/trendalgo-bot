"""Sprint 12 platform extension tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from trendalgo.api.app import create_app
from trendalgo.api.state import default_state
from trendalgo.billing.onchain_receipts import issue_fee_receipt, verify_fee_receipt
from trendalgo.data.onchain_sentiment import onchain_sentiment_stub
from trendalgo.db.postgres_adapter import PostgresDualWrite
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.onchain import preview_onchain_wallet, sync_onchain_wallet
from trendalgo.scanner.forager import forage_pairs
from trendalgo.trading.funding import fetch_funding_rates, funding_profit_estimate
from trendalgo.trading.multi_exchange import list_supported_exchanges, route_order


def test_onchain_sync_and_forager(tmp_path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    preview = preview_onchain_wallet("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
    assert preview["read_only"] and preview["total_usd"] > 0
    synced = sync_onchain_wallet(
        store,
        "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        dry_run=True,
    )
    assert synced["dry_run"] and synced["holdings"]
    forager = forage_pairs()
    assert forager["pair_count"] >= 1 and forager["pairs"][0]["forager_score"]


def test_trading_funding_and_receipts() -> None:
    assert "kraken" in list_supported_exchanges()
    order = route_order("kraken", "BTC/USD", "buy", 0.01, dry_run=True)
    assert order["mode"] == "dry_run"
    funding = fetch_funding_rates()
    assert funding["rows"]
    est = funding_profit_estimate(1000.0, 0.01)
    assert est["estimated_daily_usd"] != 0
    receipt = issue_fee_receipt("2026-06", 25.0, wallet="0xabc")
    verified = verify_fee_receipt(
        receipt["receipt_id"],
        "0xdeadbeef",
        receipt["verification_hash"],
    )
    assert verified["on_chain_stub"]


def test_postgres_adapter_and_sentiment() -> None:
    adapter = PostgresDualWrite()
    status = adapter.status()
    assert status["sqlite_mvp"] and status["schema_exists"]
    migrate = adapter.dry_run_migrate()
    assert migrate["ok"] and migrate["statement_count"] >= 3
    stub = onchain_sentiment_stub("BTC")
    assert stub["asset"] == "BTC" and stub["prototype"]


def test_platform_api_routes() -> None:
    client = TestClient(create_app(default_state()))
    assert client.get("/api/v1/platform/forager").status_code == 200
    assert client.get("/api/v1/platform/funding").status_code == 200
    assert client.get("/api/v1/platform/postgres/status").status_code == 200
    sync = client.post(
        "/api/v1/platform/onchain/sync",
        json={"address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"},
    )
    assert sync.status_code == 200
    route = client.post(
        "/api/v1/platform/trading/route",
        json={"exchange": "kraken", "pair": "BTC/USD", "side": "buy", "amount": 0.01},
    )
    assert route.status_code == 200 and route.json()["mode"] == "dry_run"
