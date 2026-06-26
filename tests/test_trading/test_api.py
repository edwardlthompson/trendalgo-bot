"""S16 trading API route tests."""

from fastapi.testclient import TestClient

from trendalgo.api.app import create_app


def test_exchange_control_api() -> None:
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

    go_live = client.post("/api/v1/trading/exchanges/gemini/go-live")
    assert go_live.status_code == 200
    assert go_live.json()["exchange"]["go_live_approved"] is True

    adapters = client.get("/api/v1/trading/adapters")
    assert "coinbaseadvanced" in adapters.json()["adapters"]
