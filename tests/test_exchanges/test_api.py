"""Exchange API route tests."""

from fastapi.testclient import TestClient

from trendalgo.api.app import create_app


def test_exchanges_registry_endpoint() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/v1/exchanges/registry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 6
    trading = [e for e in data["exchanges"] if e.get("trading_enabled")]
    assert len(trading) == 9
    portfolio = [e for e in data["exchanges"] if e["portfolio_enabled"]]
    ids = {e["id"] for e in portfolio}
    assert "kraken" in ids
    assert "coinbaseadvanced" in ids
    assert "binance" in ids
