"""Smoke: every catalog module can be packed onto the Dashboard grid."""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from tests.test_device.test_device_portfolio import _seed
from trendalgo.device.context import open_context
from trendalgo.device.portfolio_grid_pack import pack_placements, required_rows
from trendalgo.device.portfolio_layout_prefs import Placement, active_page, save_prefs
from trendalgo.device.portfolio_module_catalog import CATALOG, MODULE_IDS
from trendalgo.device.views.modules import build_module
from trendalgo.device.views.portfolio_page import PortfolioPage


def test_pack_all_catalog_modules_no_overlap() -> None:
    ids = [m.id for m in CATALOG]
    packed = pack_placements(ids, cols=24)
    assert {p.id for p in packed} == MODULE_IDS
    assert len(packed) == len(CATALOG)
    # No overlapping rects.
    for i, a in enumerate(packed):
        for b in packed[i + 1 :]:
            assert not (
                a.col < b.col + b.w
                and b.col < a.col + a.w
                and a.row < b.row + b.h
                and b.row < a.row + a.h
            ), f"overlap {a.id} vs {b.id}"
    assert required_rows(packed) >= 12


def test_dashboard_builds_every_catalog_module(qtbot: QtBot, tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _seed(profile / "portfolio.db")
    ctx = open_context(profile)
    page = PortfolioPage(ctx)
    qtbot.addWidget(page)
    page.show()
    ids = [m.id for m in CATALOG]
    packed = pack_placements(ids, existing=[], cols=page._prefs.grid.cols)
    page_layout = active_page(page._prefs)
    page_layout.placements = packed
    page._prefs.grid.rows = min(96, required_rows(packed))
    save_prefs(ctx.root, page._prefs)
    page._rebuild_canvas()
    assert set(page._modules) == MODULE_IDS
    for mid, widget in page._modules.items():
        assert widget is not None
        rebuilt = build_module(mid, ctx)
        assert rebuilt is not None


def test_customize_select_all_yields_full_catalog(qtbot: QtBot, tmp_path: Path) -> None:
    from trendalgo.device.views.portfolio_customize_dialog import PortfolioCustomizeDialog

    del tmp_path
    dialog = PortfolioCustomizeDialog([], None, cols=24)
    qtbot.addWidget(dialog)
    dialog._set_all(True)
    placed = dialog.selected_placements([])
    assert {p.id for p in placed} == MODULE_IDS
    assert all(isinstance(p, Placement) for p in placed)


def test_customize_categories_and_cross_page(qtbot: QtBot) -> None:
    from trendalgo.device.portfolio_layout_prefs import PageLayout
    from trendalgo.device.portfolio_module_catalog import catalog_by_category
    from trendalgo.device.views.portfolio_customize_dialog import PortfolioCustomizeDialog

    cats = catalog_by_category()
    assert [c for c, _ in cats] == ["Overview", "Analytics", "Trading", "More"]
    pages = [
        PageLayout(
            id="overview",
            name="Overview",
            placements=[Placement(id="total_worth", col=0, row=0, w=16, h=5)],
        ),
        PageLayout(
            id="trading",
            name="Trading",
            placements=[Placement(id="open_orders", col=0, row=0, w=12, h=4)],
        ),
    ]
    dialog = PortfolioCustomizeDialog(
        pages[0].placements,
        None,
        cols=24,
        pages=pages,
        active_page_id="overview",
    )
    qtbot.addWidget(dialog)
    assert dialog._boxes["total_worth"].isChecked()
    assert dialog._boxes["open_orders"].isChecked()
    assert "Trading" in dialog._boxes["open_orders"].text()
    # Elsewhere-only stays off current page on OK.
    placed = dialog.selected_placements(pages[0].placements)
    assert {p.id for p in placed} == {"total_worth"}
    # Uncheck elsewhere module → reported for purge.
    dialog._boxes["open_orders"].setChecked(False)
    assert "open_orders" in dialog.removed_from_other_pages()


def test_coin_allocation_hides_legend_no_asset_name(qtbot: QtBot) -> None:
    from types import SimpleNamespace

    from trendalgo.device.views.modules.allocation_modules import CoinAllocationModule

    widget = CoinAllocationModule()
    qtbot.addWidget(widget)
    chart = widget._view.chart()
    assert chart is not None
    assert chart.legend().isVisible() is False
    overview = SimpleNamespace(
        allocation=[{"asset": "SOL", "value_usd": 100.0, "pct": 100.0}],
    )
    widget.set_overview(overview, range_key="1y")  # type: ignore[arg-type]
    assert "SOL" not in widget._center.text()
    assert "SOL" in widget._legend.text()
