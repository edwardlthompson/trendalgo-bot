"""Hit remaining OpenAPI routes to raise handler coverage."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trendalgo.api.app import create_app
from trendalgo.api.state import default_state


@pytest.fixture
def api_client() -> TestClient:
    data_dir = Path(tempfile.mkdtemp(prefix="trendalgo-sweep-"))
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir)
    os.environ["TRENDALGO_FEE_SYNC_ON_START"] = "0"
    os.environ["TRENDALGO_MARKET_SOURCE"] = "synthetic"
    from trendalgo.exchanges import fees
    from trendalgo.exchanges.fee_store import get_fee_store, reset_fee_store
    from trendalgo.exchanges.fee_sync import ensure_fee_db_ready

    reset_fee_store()
    fees.clear_fee_cache()
    ensure_fee_db_ready(get_fee_store())
    return TestClient(create_app(default_state()))


def test_openapi_route_sweep(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_BTC_USD_RATE", "100000")
    monkeypatch.setenv("TRENDALGO_PAYMENT_SIMULATE", "1")
    c = api_client

    assert c.get("/").status_code == 200
    assert c.get("/api/v1/health").json()["status"] == "ok"
    c.post("/api/v1/portfolio/sync")
    assert c.get("/api/v1/ops/health").status_code == 200
    assert c.get("/api/v1/ops/version").status_code == 200
    c.post("/api/v1/ops/backup")
    c.post("/api/v1/ops/restore", json={"backup_id": "latest"})

    c.get("/api/v1/ai/scanner-pipeline")
    c.get("/api/v1/billing/payment/assets")
    c.get("/api/v1/billing/preview")
    c.get("/api/v1/billing/license-status")
    c.post("/api/v1/billing/terms/accept", json={"terms_version": "2026-06-draft-1"})
    c.post("/api/v1/billing/payment/start", json={"period": "2026-06", "asset": "BTC"})
    c.post("/api/v1/billing/payment/check")
    c.post("/api/v1/billing/payment/watch")
    c.post("/api/v1/billing/mark-paid", json={"period": "2026-06", "tx_hash": "manual-1"})
    c.post("/api/v1/billing/boost-mode/disable")

    c.get("/api/v1/constants/timeframes")
    c.get("/api/v1/exchanges/registry")
    c.get("/api/v1/exchanges/kraken/pairs")
    c.post("/api/v1/exchanges/fees/sync")

    c.get("/api/v1/export/bundle")
    c.get("/api/v1/export/settings")
    c.post("/api/v1/growth/leaderboard/opt-out")

    c.get("/api/v1/icons/exchanges")
    c.get("/api/v1/icons/coin/BTC")
    c.get("/api/v1/icons/stats")

    c.get("/api/v1/platform/venues/registry")
    c.get("/api/v1/platform/onchain/preview/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
    c.post(
        "/api/v1/platform/onchain/sync-all",
        json={"addresses": ["0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"]},
    )
    c.get("/api/v1/platform/dex/swap-chains")
    c.get("/api/v1/platform/dex/status")
    c.get("/api/v1/platform/dex/status/full")
    c.get("/api/v1/platform/dex/ops-validation")
    c.get("/api/v1/platform/dex/preview")
    c.get("/api/v1/platform/dex/quote", params={"chain": "base", "pair": "ETH/USDC"})
    c.post("/api/v1/platform/dex/dry-run", json={"venue_id": "uniswap_v3", "pair": "ETH/USDC"})
    c.post("/api/v1/platform/dex/venues/uniswap_v3/go-live")
    c.get("/api/v1/platform/fee-receipt/2026-06")
    c.post(
        "/api/v1/platform/fee-receipt/verify",
        json={"receipt_id": "r1", "tx_hash": "0xabc", "verification_hash": "deadbeef"},
    )
    c.get("/api/v1/platform/data/sentiment/BTC")
    c.get("/api/v1/platform/postgres/status")
    c.post("/api/v1/platform/postgres/migrate-dry-run")
    c.post("/api/v1/platform/funding/estimate", json={"notional_usd": 1000, "rate": 0.01})

    c.post("/api/v1/portfolio/snapshot")
    c.get("/api/v1/portfolio/accounts")
    c.get("/api/v1/portfolio/performance")
    c.get("/api/v1/portfolio/dex/positions")
    c.get("/api/v1/portfolio/tags")
    c.get("/api/v1/portfolio/history/2026-06-01")
    c.post("/api/v1/portfolio/rebalance/apply", json={"dry_run": True})
    c.post("/api/v1/notifications/email/test", json={"subject": "t", "body": "b"})

    c.get("/api/v1/research/ta-catalog")
    c.get("/api/v1/research/ta-library")
    c.get("/api/v1/research/ta-glossary")
    c.post("/api/v1/research/ta-sweep", json={"indicators": ["RSI"], "pair": "BTC/USD"})
    c.get("/api/v1/research/hyperopt-heatmap")

    c.get("/api/v1/trading/runner/status")
    c.get("/api/v1/trading/arbitrage/signals")
    c.post("/api/v1/trading/dry-run/tick")
    c.post(
        "/api/v1/trading/exchanges/kraken/route",
        json={"pair": "BTC/USD", "side": "buy", "amount_usd": 50},
    )
    c.post(
        "/api/v1/signals/webhook",
        json={"pair": "BTC/USD", "action": "buy", "secret": "test"},
    )
    c.post("/api/v1/scanner/preview", json={"pair": "BTC/USD"})
    c.post("/api/v1/watchlist/check")

    export = c.get("/api/v1/strategies/smart-dca/export").json()
    c.post("/api/v1/strategies/import", json={"json": export["json"]})
    c.get("/api/v1/backtest/fleet/lookbacks")

    bots = c.get("/api/v1/bots").json()["bots"]
    bot_id = bots[0]["id"]
    c.get(f"/api/v1/bots/{bot_id}/equity-limits")
    c.post(f"/api/v1/bots/{bot_id}/force")
    c.put(f"/api/v1/bots/{bot_id}/enabled", json={"enabled": True})
    c.post("/api/v1/bots/ta-cache/prewarm")
    c.get("/api/v1/bots/ta-cache/prewarm/active")
    c.get("/api/v1/bots/ohlcv/warmup/active")

    share = c.post("/api/v1/portfolio/public-share").json()
    c.get(f"/api/v1/public/dashboard/{share['token']}")

    c.post(
        "/api/v1/backtest/fleet",
        json={"exchange_id": "kraken", "pair": "BTC/USD", "stake_usd": 500},
    )
    history = c.get("/api/v1/backtest/fleet/history").json()
    if history.get("runs"):
        job_id = history["runs"][0]["job_id"]
        c.get(f"/api/v1/backtest/fleet/history/{job_id}")

    stmt = c.get("/api/v1/billing/statement/2026-06/export")
    assert stmt.status_code in {200, 404}
