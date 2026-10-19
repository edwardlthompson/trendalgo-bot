"""Device portfolio path and read-only overview (no shared-file create)."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.device.portfolio_compare import local_comparison_curves
from trendalgo.device.portfolio_model import load_overview, portfolio_db_path
from trendalgo.device.profile import DATA_ENV, PORTFOLIO_ENV
from trendalgo.device.stores import StoreReadError, read_portfolio
from trendalgo.portfolio.db import HoldingRow, PortfolioStore


def _seed(path: Path, *, with_daily: bool = True) -> Path:
    store = PortfolioStore(path, create=True)
    account_id = store.get_or_create_account("kraken", "default")
    store.insert_snapshot(
        account_id,
        total_usd=1500.0,
        holdings=[
            HoldingRow("BTC", 0.01, 100_000.0, 1000.0, cost_basis_usd=900.0),
            HoldingRow("ETH", 0.5, 1000.0, 500.0, cost_basis_usd=400.0),
        ],
        source="test",
    )
    if with_daily:
        store.upsert_daily_aggregate(
            account_id,
            date="2026-10-09",
            total_usd=1400.0,
            daily_pnl_usd=0.0,
            realized_pnl_usd=0.0,
            unrealized_pnl_usd=0.0,
        )
        store.upsert_daily_aggregate(
            account_id,
            date="2026-10-10",
            total_usd=1500.0,
            daily_pnl_usd=100.0,
            realized_pnl_usd=0.0,
            unrealized_pnl_usd=100.0,
        )
    return path


def test_missing_file_returns_none(tmp_path: Path) -> None:
    assert portfolio_db_path(tmp_path) is None
    assert read_portfolio(None) is None
    assert read_portfolio(tmp_path / "missing.db") is None


def test_prefers_launcher_under_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = tmp_path / "data"
    launcher = data / "launcher" / "portfolio.db"
    shared = data / "portfolio.db"
    _seed(launcher)
    _seed(shared)
    monkeypatch.setenv(DATA_ENV, str(data))
    assert portfolio_db_path(tmp_path / "profile") == launcher


def test_override_beats_launcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = tmp_path / "data"
    launcher = data / "launcher" / "portfolio.db"
    other = tmp_path / "other.db"
    _seed(launcher)
    _seed(other)
    monkeypatch.setenv(DATA_ENV, str(data))
    monkeypatch.setenv(PORTFOLIO_ENV, str(other))
    assert portfolio_db_path(tmp_path / "profile") == other


def test_load_overview_reads_holdings_and_equity(tmp_path: Path) -> None:
    path = _seed(tmp_path / "portfolio.db")
    overview = load_overview(path)
    assert overview is not None
    assert overview.net_worth_usd == 1500.0
    assert len(overview.holdings) == 2
    assert overview.daily_pnl_usd == 100.0
    assert [p["total_usd"] for p in overview.equity] == [1400.0, 1500.0]


def test_create_false_does_not_create_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.db"
    with pytest.raises(FileNotFoundError):
        PortfolioStore(missing, create=False)
    assert not missing.exists()


def test_local_comparison_curves_need_two_points() -> None:
    one = [{"captured_at": "2026-10-10", "total_usd": 100.0}]
    assert local_comparison_curves(one) == ([], [])
    two = [
        {"captured_at": "2025-01-01", "total_usd": 100.0},
        {"captured_at": "2025-06-01", "total_usd": 110.0},
    ]
    top10, buy_hold = local_comparison_curves(two)
    assert len(top10) == 2
    assert len(buy_hold) == 2
    assert top10[0]["total_usd"] == 100.0
    assert buy_hold[-1]["total_usd"] != 100.0


def test_load_overview_at_snapshot_date(tmp_path: Path) -> None:
    path = tmp_path / "portfolio.db"
    store = PortfolioStore(path, create=True)
    account_id = store.get_or_create_account("kraken", "default")
    store.insert_snapshot_at(
        account_id,
        1400.0,
        [HoldingRow("BTC", 0.01, 100_000.0, 1000.0, cost_basis_usd=900.0)],
        captured_at="2026-10-09T08:00:00+00:00",
        source="test",
    )
    store.insert_snapshot_at(
        account_id,
        1500.0,
        [HoldingRow("BTC", 0.01, 100_000.0, 1000.0, cost_basis_usd=900.0)],
        captured_at="2026-10-10T08:00:00+00:00",
        source="test",
    )
    older = load_overview(path, as_of_date="2026-10-09")
    latest = load_overview(path)
    assert older is not None and latest is not None
    assert older.net_worth_usd == 1400.0
    assert latest.net_worth_usd == 1500.0
    assert len(latest.snapshot_dates) == 2


def test_read_portfolio_wraps_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "portfolio.db"
    path.write_text("not sqlite", encoding="utf-8")
    with pytest.raises(StoreReadError):
        read_portfolio(path)
