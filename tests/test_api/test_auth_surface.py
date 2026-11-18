"""AUTH-01…05 acceptance tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trendalgo.api.app import _cors_origins, create_app
from trendalgo.api.deps import EXEMPT_MUTATING, MUTATING_METHODS
from trendalgo.api.session_tokens import BearerTokenStore
from trendalgo.api.state import default_state
from trendalgo.device.api_bearer import load_api_bearer, save_api_bearer
from trendalgo.device.wizard.credentials import MemoryCredentialStore


def _authed_client(*, secret: str = "test-owner-secret") -> tuple[TestClient, object]:
    data_dir = Path(tempfile.mkdtemp(prefix="trendalgo-auth-"))
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir)
    os.environ["TRENDALGO_FEE_SYNC_ON_START"] = "0"
    os.environ["TRENDALGO_OWNER_SECRET"] = secret
    os.environ["TRENDALGO_OWNER_ID"] = "owner-1"
    from trendalgo.exchanges import fees
    from trendalgo.exchanges.fee_store import get_fee_store, reset_fee_store
    from trendalgo.exchanges.fee_sync import ensure_fee_db_ready

    reset_fee_store()
    fees.clear_fee_cache()
    ensure_fee_db_ready(get_fee_store())
    state = default_state()
    app = create_app(state)
    issued = state.bearer_store.mint()
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {issued.token}"})
    return client, state


def test_mutating_routes_require_auth() -> None:
    data_dir = Path(tempfile.mkdtemp(prefix="trendalgo-auth-open-"))
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir)
    os.environ["TRENDALGO_FEE_SYNC_ON_START"] = "0"
    os.environ.pop("TRENDALGO_OWNER_SECRET", None)
    from trendalgo.exchanges import fees
    from trendalgo.exchanges.fee_store import get_fee_store, reset_fee_store
    from trendalgo.exchanges.fee_sync import ensure_fee_db_ready

    reset_fee_store()
    fees.clear_fee_cache()
    ensure_fee_db_ready(get_fee_store())
    app = create_app(default_state())
    client = TestClient(app)

    mutating: list[tuple[str, str]] = []
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            if method.upper() in MUTATING_METHODS:
                mutating.append((method.upper(), path))

    assert mutating, "expected mutating routes from OpenAPI table"
    for method, path in mutating:
        key = (method, path)
        if key in EXEMPT_MUTATING:
            continue
        resp = client.request(method, path)
        assert resp.status_code in {401, 403, 405, 422}, (
            f"{method} {path} must refuse unauthenticated callers, got {resp.status_code}"
        )

    assert ("POST", "/api/v1/webhooks/tradingview") in EXEMPT_MUTATING
    assert ("POST", "/api/v1/webhooks/tradingview") in mutating


def test_health_and_version_open() -> None:
    client, _ = _authed_client()
    # Strip auth to prove exempt GETs stay open.
    bare = TestClient(client.app)
    assert bare.get("/api/v1/health").status_code == 200
    assert bare.get("/api/v1/version").status_code == 200


def test_cors_default_empty_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRENDALGO_CORS_ORIGINS", raising=False)
    assert _cors_origins() == []
    monkeypatch.setenv("TRENDALGO_CORS_ORIGINS", "https://a.example, https://b.example")
    assert _cors_origins() == ["https://a.example", "https://b.example"]


def test_tradingview_hmac_and_body_once(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "tv-secret"
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_SECRET", secret)
    client, _ = _authed_client()
    bare = TestClient(client.app)
    payload = json.dumps({"pair": "BTC/USD", "action": "buy"}).encode()

    unsigned = bare.post("/api/v1/webhooks/tradingview", content=payload)
    assert unsigned.status_code == 200
    assert unsigned.json()["accepted"] is False

    bad_sig = bare.post(
        "/api/v1/webhooks/tradingview",
        content=payload,
        headers={"X-Signature": "deadbeef"},
    )
    assert bad_sig.json()["accepted"] is False

    good = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    ok = bare.post(
        "/api/v1/webhooks/tradingview",
        content=payload,
        headers={"X-Signature": good},
    )
    body = ok.json()
    assert body["accepted"] is True
    assert body["payload_digest"] == hashlib.sha256(payload).hexdigest()


def test_tradingview_body_read_once_via_counting_wrapper() -> None:
    from trendalgo.api.deps import read_raw_body_once

    class CountingRequest:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload
            self.reads = 0

        async def body(self) -> bytes:
            self.reads += 1
            return self._payload

    req = CountingRequest(b'{"pair":"BTC/USD","action":"buy"}')
    import asyncio

    raw = asyncio.run(read_raw_body_once(req))  # type: ignore[arg-type]
    assert req.reads == 1
    assert raw.payload.startswith(b"{")


def test_tradingview_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from trendalgo.portfolio.db import PortfolioStore
    from trendalgo.signals.tradingview import TradingViewWebhook

    data_dir = Path(tempfile.mkdtemp(prefix="tv-rl-"))
    store = PortfolioStore(data_dir / "p.db")
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_SECRET", "s")
    handler = TradingViewWebhook(store, secret="s", max_per_minute=3)
    payload = b'{"pair":"BTC/USD","action":"buy"}'
    sig = hmac.new(b"s", payload, hashlib.sha256).hexdigest()
    for _ in range(3):
        assert handler.handle(payload, client_ip="1.2.3.4", signature=sig).accepted
    tripped = handler.handle(payload, client_ip="1.2.3.4", signature=sig)
    assert tripped.accepted is False
    assert "rate" in tripped.reason


def test_bearer_expiry_and_revoke() -> None:
    clock = {"t": 1_000}

    def now() -> int:
        return clock["t"]

    store = BearerTokenStore(ttl_s=10, clock=now)
    issued = store.mint()
    assert store.verify(issued.token)
    clock["t"] = 1_020
    assert store.verify(issued.token) is False

    clock["t"] = 1_000
    issued2 = store.mint()
    store.revoke(issued2.token)
    assert store.verify(issued2.token) is False


def test_bearer_rejected_by_api() -> None:
    client, state = _authed_client()
    bare = TestClient(client.app)
    resp = bare.post("/api/v1/risk/pause", headers={"Authorization": "Bearer not-a-token"})
    assert resp.status_code == 401

    issued = state.bearer_store.mint()
    state.bearer_store.revoke(issued.token)
    resp2 = bare.post(
        "/api/v1/risk/pause",
        headers={"Authorization": f"Bearer {issued.token}"},
    )
    assert resp2.status_code == 401


def test_keyring_miss_requires_repair() -> None:
    vault = MemoryCredentialStore()
    load = load_api_bearer(vault)
    assert load.must_repair is True
    assert load.token is None
    save_api_bearer("tok-1", vault)
    ok = load_api_bearer(vault)
    assert ok.must_repair is False
    assert ok.token == "tok-1"


def test_prod_compose_loopback_binding() -> None:
    text = Path("docker/docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "127.0.0.1:8080:8080" in text
    assert '"8080:8080"' not in text.replace("127.0.0.1:8080:8080", "")
