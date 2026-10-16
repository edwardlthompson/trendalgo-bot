"""Qt smoke for the Portfolio page (tabs, demo, Share)."""

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
    assert page._share.text() == S.PORTFOLIO_SHARE
    assert page._tabs.count() == 4
    assert page._chart._view.minimumHeight() >= 320
    assert page._overview is not None
    assert len(page._overview.holdings) == 20


def test_seeded_portfolio_shows_load_demo_and_share(qtbot: QtBot, tmp_path: Path) -> None:
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
    assert page._share.text() == S.PORTFOLIO_SHARE
    assert "$1,500.00" in page._hero._net._value.text()
    page._toggle_demo()
    assert not page._demo.isHidden()
    assert page._overview is not None
    assert len(page._overview.holdings) == 20
    page._toggle_demo()
    assert page._demo.isHidden()
    assert "$1,500.00" in page._hero._net._value.text()


def test_multi_snapshot_shows_timeline_scrubber(qtbot: QtBot, tmp_path: Path) -> None:
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
    assert page._timeline._combo.count() == 2
    assert page._timeline._row.isVisible()
    assert page._chart._chart.legend().isVisible()


def test_share_png_writes_export(qtbot: QtBot, tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _seed(profile / "portfolio.db")
    ctx = open_context(profile)
    page = PortfolioPage(ctx)
    qtbot.addWidget(page)
    page.show()
    page._share_png()
    exports = list((profile / "exports").glob("portfolio-*.png"))
    assert exports, "expected Share PNG under exports/"
