"""Layout guard (offscreen): content follows the subtitle, fields share a top line, one primary action.

Skipped when PySide6 or pytest-qt is missing, like the other Qt tests.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtWidgets import QLabel, QWidget  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.views.backtest_page import BacktestPage  # noqa: E402
from trendalgo.device.views.main_window import MainWindow  # noqa: E402
from trendalgo.device.views.plan_page import PlanPage  # noqa: E402
from trendalgo.device.views.settings_page import SettingsPage  # noqa: E402
from trendalgo.device.views.status_page import StatusPage  # noqa: E402
from trendalgo.device.workers import WorkerPool  # noqa: E402


def _shown(qtbot: QtBot, page: QWidget) -> QWidget:
    qtbot.addWidget(page)
    page.resize(1100, 900)
    page.show()
    qtbot.waitExposed(page)
    return page


def _top(widget: QWidget, page: QWidget) -> int:
    return widget.mapTo(page, QPoint(0, 0)).y()


def _bottom(widget: QWidget, page: QWidget) -> int:
    return _top(widget, page) + widget.height()


def test_settings_content_sits_right_under_the_subtitle(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = _shown(qtbot, SettingsPage(ctx))
    header = page.layout().itemAt(0).widget()
    subtitle = header.findChildren(QLabel)[1]
    first_content = page.layout().itemAt(1).widget()
    gap = _top(first_content, page) - _bottom(subtitle, page)
    assert 0 <= gap <= 16


def test_backtest_pair_and_scan_share_the_form(
    qtbot: QtBot, ctx: DeviceContext, pool: WorkerPool
) -> None:
    page = _shown(qtbot, BacktestPage(ctx, pool))
    assert page._pair.isVisible()
    assert page._run.isVisible()
    assert page._share.isVisible()
    assert not hasattr(page, "_activity")
    assert abs(_top(page._pair, page) - _top(page._run, page)) <= 2


def test_plan_fields_in_one_row_share_a_top_line(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = _shown(qtbot, PlanPage(ctx))
    assert _top(page._pair, page) == _top(page._timeframe, page)


def test_each_view_marks_one_primary_action(
    qtbot: QtBot, ctx: DeviceContext, pool: WorkerPool
) -> None:
    backtest = BacktestPage(ctx, pool)
    plan = PlanPage(ctx)
    settings = SettingsPage(ctx)
    for page in (backtest, plan, settings):
        qtbot.addWidget(page)
    assert backtest._run.property("role") == "primary"
    assert backtest._cancel.property("role") != "primary"
    assert plan._send.property("role") == "primary"
    assert plan._save.property("role") != "primary"
    assert plan._add.property("role") != "primary"
    assert settings._save.property("role") == "primary"


def test_the_window_opens_at_720_pixels_because_settings_scrolls(
    qtbot: QtBot, ctx: DeviceContext, pool: WorkerPool
) -> None:
    window = MainWindow(ctx, pool, [])
    qtbot.addWidget(window)
    # Stack min hint can exceed 720 (tall pages); the shell itself starts at 720.
    assert window.height() == 720


def test_status_reload_button_keeps_its_own_width(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = _shown(qtbot, StatusPage(ctx, lambda: None))
    assert page._reload.width() < page.width() // 2
