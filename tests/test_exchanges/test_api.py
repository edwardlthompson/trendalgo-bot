"""Exchange API route tests."""

from tests.support.api_client import make_api_client


def test_exchanges_registry_endpoint() -> None:
    client = make_api_client()
    resp = client.get("/api/v1/exchanges/registry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 7
    trading = [e for e in data["exchanges"] if e.get("trading_enabled")]
    assert len(trading) == 9
    portfolio = [e for e in data["exchanges"] if e["portfolio_enabled"]]
    ids = {e["id"] for e in portfolio}
    assert "kraken" in ids
    assert "coinbaseadvanced" in ids
    assert "binance" in ids
