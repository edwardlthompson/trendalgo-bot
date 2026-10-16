"""S16 trading API route tests (owner-signed go-live, H2/H3)."""

import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trendalgo.api.app import create_app
from trendalgo.trading.signed_command import OWNER_ID_ENV, OWNER_SECRET_ENV, sign_request

OWNER_ID = "owner-test"
OWNER_SECRET = "owner-secret-for-api-tests-only"


def _owner_headers(monkeypatch: pytest.MonkeyPatch, path: str) -> dict[str, str]:
    monkeypatch.setenv(OWNER_ID_ENV, OWNER_ID)
    monkeypatch.setenv(OWNER_SECRET_ENV, OWNER_SECRET)
    return sign_request(
        method="POST",
        path=path,
        body=b"",
        owner_id=OWNER_ID,
        secret=OWNER_SECRET,
        timestamp=int(time.time()),
        nonce=uuid.uuid4().hex,
    )


def test_exchange_control_api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    client = TestClient(create_app())
    status = client.get("/api/v1/trading/exchanges/control")
    assert status.status_code == 200
    exchanges = status.json()["exchanges"]
    ids = {e["exchange_id"] for e in exchanges}
    assert "coinbaseadvanced" in ids
    assert "gemini" in ids

    pause = client.put("/api/v1/trading/exchanges/kraken/pause", json={"paused": True})
    assert pause.status_code == 200
    assert pause.json()["exchange"]["paused"] is True

    path = "/api/v1/trading/exchanges/gemini/go-live"
    unsigned = client.post(path)
    assert unsigned.status_code == 403  # H2/H3: no approval without the owner's signature
    go_live = client.post(path, headers=_owner_headers(monkeypatch, path))
    assert go_live.status_code == 200
    assert go_live.json()["exchange"]["go_live_approved"] is True

    adapters = client.get("/api/v1/trading/adapters")
    assert "coinbaseadvanced" in adapters.json()["adapters"]
