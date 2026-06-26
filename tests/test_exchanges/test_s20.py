"""S20 N-exchange ops validation tests."""

from __future__ import annotations

from trendalgo.exchanges.load_test import (
    run_n_exchange_ops_validation,
    run_trading_status_check,
)


def test_trading_status_nine_venues_phase2() -> None:
    report = run_trading_status_check()
    assert report["ok"] is True
    assert report["registry_version"] == 6
    assert report["worldwide_trading_phase"] == 2
    assert int(report["trading_exchange_count"]) == 9
    assert set(report["worldwide_exchanges"]) == {"binance", "bybit", "okx"}


def test_n_exchange_ops_validation() -> None:
    report = run_n_exchange_ops_validation()
    assert report["ok"] is True
    assert report["portfolio_sync"]["ok"] is True
    assert report["trading_status"]["ok"] is True
    assert int(report["portfolio_sync"]["exchange_count"]) == 9


def test_runner_status_api_matches_trading_check() -> None:
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    expected = run_trading_status_check()
    client = TestClient(create_app())
    body = client.get("/api/v1/trading/runner/status").json()
    assert body["engine"] == "native"
    assert body["worldwide_trading_phase"] == expected["worldwide_trading_phase"]
    assert len(body["exchanges"]) == expected["trading_exchange_count"]
    assert set(body["worldwide_exchanges"]) == set(expected["worldwide_exchanges"])
