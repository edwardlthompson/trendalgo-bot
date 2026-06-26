"""Dry-run runner tests (S15 CM-1)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.risk.journal import TradeJournal
from trendalgo.strategies.runtime.contract import Candle
from trendalgo.strategies.runtime.loader import load_strategy
from trendalgo.trading.runner.dry_run import DryRunRunner


def _candle(ts: int, close: float) -> Candle:
    return Candle(timestamp_ms=ts, open=close, high=close, low=close, close=close, volume=1)


def test_dry_run_tick_journals_entry(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "journal.db")
    strategy = load_strategy("grid-trading")
    runner = DryRunRunner(
        strategy=strategy,
        journal=journal,
        exchange_id="kraken",
        pair="BTC/USD",
    )
    for i in range(50):
        runner.tick(_candle(i * 300_000, 100 - i * 0.5))
    assert journal.count_trades() >= 0
    status = runner.tick(_candle(50 * 300_000, 70))
    assert status["engine"] == "native"
    assert status["exchange_id"] == "kraken"


def test_runner_status_api() -> None:
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/trading/runner/status")
    assert resp.status_code == 200
    assert resp.json()["engine"] == "native"
