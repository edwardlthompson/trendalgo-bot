"""Qt smoke for the Dashboard (modular portfolio page)."""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from tests.test_device.test_device_portfolio import _seed
from trendalgo.device import strings as S
from trendalgo.device.context import open_context
from trendalgo.device.portfolio_model import portfolio_db_path
from trendalgo.device.views.portfolio_page import PortfolioPage
from trendalgo.portfolio.db import HoldingRow, PortfolioStore


def test_empty_portfolio_seeds_demo(qtbot: QtBot, tmp_path: Path) -> None:
    ctx = open_context(tmp_path / "profile")
    page = PortfolioPage(ctx)
    qtbot.addWidget(page)
    assert not page._demo.isHidden()
    assert page._demo_btn.text() == S.PORTFOLIO_EXIT_DEMO
    assert page._sync.text() == S.PORTFOLIO_SYNC_ALL
    assert page._tabs.count() == 3
    assert page._overview is not None
    assert len(page._overview.holdings) == 20
    assert "total_worth" in page._modules


def test_seeded_portfolio_shows_load_demo(qtbot: QtBot, tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    path = _seed(profile / "portfolio.db")
    ctx = open_context(profile)
    assert ctx.portfolio_path == path
    assert portfolio_db_path(profile) == path
    page = PortfolioPage(ctx)
    qtbot.addWidget(page)
    page.show()
    assert page._demo.isHidden()
    assert page._demo_btn.text() == S.PORTFOLIO_LOAD_DEMO
    assert page._overview is not None
    assert page._overview.net_worth_usd == 1500.0
    page._toggle_demo()
    assert not page._demo.isHidden()
    assert page._overview is not None
    assert len(page._overview.holdings) == 20
    page._toggle_demo()
    assert page._demo.isHidden()
    assert page._overview is not None
    assert page._overview.net_worth_usd == 1500.0


def test_multi_snapshot_loads_overview(qtbot: QtBot, tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    path = profile / "portfolio.db"
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
    store.upsert_daily_aggregate(account_id, "2026-10-09", 1400.0, 0.0, 0.0, 0.0)
    store.upsert_daily_aggregate(account_id, "2026-10-10", 1500.0, 100.0, 0.0, 100.0)
    ctx = open_context(profile)
    assert ctx.portfolio_path == path
    page = PortfolioPage(ctx)
    qtbot.addWidget(page)
    page.show()
    assert page._overview is not None
    assert page._overview.net_worth_usd == 1500.0
    assert page._tabs.count() >= 1


def test_nav_label_is_dashboard() -> None:
    assert S.NAV_PORTFOLIO == "Dashboard"
    assert S.PORTFOLIO_TITLE == "Dashboard"


def test_export_page_png_writes_export(qtbot: QtBot, tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _seed(profile / "portfolio.db")
    ctx = open_context(profile)
    page = PortfolioPage(ctx)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    dest = profile / "exports" / "portfolio-page-overview-test.png"
    # Skip the save dialog / message box in automated tests.
    page._show_share_done = lambda _out: None  # type: ignore[method-assign]
    page._export_page_png(dest=dest)
    assert dest.is_file() and dest.stat().st_size > 0
