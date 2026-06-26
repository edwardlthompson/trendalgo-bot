"""Native walk-forward tests (S17 CM-3)."""

from trendalgo.trading.backtest.walk_forward import fixture_candles, run_native_walk_forward


def test_native_walk_forward_complete() -> None:
    candles = fixture_candles(count=100)
    result = run_native_walk_forward("grid-trading", candles, pair="BTC/USD")
    assert result["engine"] == "native"
    assert result["status"] == "complete"
    assert result["fold_count"] >= 1
    assert "avg_test_pnl" in result


def test_native_walk_forward_api() -> None:
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/research/walk-forward",
        json={"strategy": "grid-trading", "pair": "BTC/USD", "use_native": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["engine"] == "native"
    assert body["fold_count"] >= 1
