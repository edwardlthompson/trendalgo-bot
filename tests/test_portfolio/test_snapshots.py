"""Portfolio snapshot scheduler tests."""

from __future__ import annotations

from pathlib import Path

from trendalgo.portfolio import snapshots
from trendalgo.portfolio.db import PortfolioStore


def test_capture_portfolio_snapshot_dry_run(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    logs: list[str] = []
    result = snapshots.capture_portfolio_snapshot(store, dry_run=True, on_log=logs.append)
    assert result["mode"] == "dry-run"
    assert result["total_usd"] > 0
    assert result["exchange_count"] >= 1
    assert logs and "portfolio snapshot" in logs[0]


def test_run_daily_notification_records_message(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    overview = {"net_worth_usd": 50_000.0, "daily_pnl_usd": 120.0}
    sent = snapshots.run_daily_notification(store, overview, dry_run=True)
    assert sent is False
    notes = store.list_notifications(limit=5)
    assert notes
    assert notes[0]["category"] == "daily_pl"


def test_scheduled_portfolio_job_runs_pipeline(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    logs: list[str] = []
    snapshots.scheduled_portfolio_job(
        store,
        lambda: {"net_worth_usd": 1_000.0, "daily_pnl_usd": 0.0, "daily_pnl_pct": 0.0},
        dry_run=True,
        on_log=logs.append,
    )
    assert logs
    assert store.list_notifications(limit=1)
