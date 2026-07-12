"""P2 backend integration coverage."""

from __future__ import annotations

import hashlib
import hmac
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from trendalgo.api.app import create_app
from trendalgo.api.state import default_state


def _client(tmp_path: Path, monkeypatch: Any) -> tuple[TestClient, Any]:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    state = default_state()
    return TestClient(create_app(state)), state


def test_telegram_ingress_allowlist_and_rate_limit(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setenv("TELEGRAM_RATE_LIMIT_PER_MINUTE", "1")
    client, state = _client(tmp_path, monkeypatch)
    update = {"message": {"chat": {"id": 42}, "text": "/pause"}}

    response = client.post("/api/v1/webhooks/telegram", json=update)
    assert response.status_code == 200
    assert response.json()["reply"] == "Trading paused"
    assert state.risk_manager.state.paused is True
    assert client.post("/api/v1/webhooks/telegram", json=update).status_code == 429

    denied = {"message": {"chat": {"id": 7}, "text": "/resume"}}
    assert client.post("/api/v1/webhooks/telegram", json=denied).status_code == 403


def test_hyperopt_job_reaches_done(tmp_path: Path, monkeypatch: Any) -> None:
    client, _ = _client(tmp_path, monkeypatch)
    queued = client.post(
        "/api/v1/hyperopt",
        json={"strategy": "smart-dca", "pair": "BTC/USD", "epochs": 10},
    ).json()
    assert queued["status"] == "queued"
    assert queued["error"] is None

    job: dict[str, Any] = queued
    for _ in range(100):
        job = client.get(f"/api/v1/hyperopt/{queued['job_id']}").json()
        if job["status"] in {"done", "failed"}:
            break
        time.sleep(0.01)
    assert job["status"] == "done"
    assert job["result"]["engine"] == "native"
    assert job["result"]["walk_forward"]["fold_count"] > 0


def test_hyperopt_job_exposes_failure(monkeypatch: Any) -> None:
    from trendalgo.backtest import hyperopt

    def fail(_profits: list[float]) -> dict[str, Any]:
        raise RuntimeError("optimizer failed")

    monkeypatch.setattr(hyperopt, "run_walk_forward", fail)
    store = hyperopt.HyperoptJobStore()
    queued = store.submit("smart-dca", "BTC/USD", 10)
    job: dict[str, Any] | None = queued
    for _ in range(100):
        job = store.get(queued["job_id"])
        if job and job["status"] == "failed":
            break
        time.sleep(0.01)
    assert job is not None
    assert job["status"] == "failed"
    assert job["error"] == "optimizer failed"


def test_tradingview_execution_is_opt_in_and_audited(tmp_path: Path, monkeypatch: Any) -> None:
    secret = "tv-secret"
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_SECRET", secret)
    client, state = _client(tmp_path, monkeypatch)
    body = b'{"pair":"BTC/USD","action":"buy","amount_usd":25}'
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    headers = {"X-Signature": signature, "Content-Type": "application/json"}

    logged = client.post("/api/v1/webhooks/tradingview", content=body, headers=headers).json()
    assert logged["execution"]["status"] == "log_only"

    monkeypatch.setenv("TV_EXECUTION_ACK", "1")
    executed = client.post("/api/v1/webhooks/tradingview", content=body, headers=headers).json()
    assert executed["execution"]["executed"] is True
    assert executed["execution"]["tick"]["mode"] == "dry_run"
    with sqlite3.connect(state.portfolio_store.db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM webhook_audit WHERE source = 'tradingview-execution'"
        ).fetchone()[0]
    assert count == 1


def test_live_arbitrage_returns_partial_results_and_timeouts(
    monkeypatch: Any,
) -> None:
    from trendalgo.portfolio import arbitrage

    def fake_fetch(entry: Any, _timeout_ms: int) -> dict[str, float]:
        if entry.id == "gemini":
            time.sleep(0.1)
        if entry.id == "kraken":
            return {"BTC/USD": 50_000.0}
        if entry.id == "binanceus":
            return {"BTC/USD": 50_500.0}
        raise RuntimeError("offline")

    monkeypatch.setattr(arbitrage, "_fetch_venue", fake_fetch)
    monkeypatch.setenv("ARBITRAGE_TIMEOUT_SECONDS", "0.02")
    result = arbitrage.detect_arbitrage_opportunities(dry_run=False)

    assert result["pricing_source"] == "live"
    assert "gemini" in result["timed_out_venues"]
    assert result["count"] == 1
    assert result["alerts"][0]["venues_compared"] == 2
