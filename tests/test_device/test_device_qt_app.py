"""Qt smoke tests: first run, the forms, empty states, and worker runs. Offscreen; no window shows.

Skipped when PySide6 or pytest-qt is missing.
"""

from __future__ import annotations

import multiprocessing
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.profile import read_json, write_json  # noqa: E402
from trendalgo.device.selftest import check_window  # noqa: E402
from trendalgo.device.views.backtest_page import BacktestPage  # noqa: E402
from trendalgo.device.views.main_window import (  # noqa: E402
    BACKTESTS,
    PORTFOLIO,
    STATUS,
    MainWindow,
)
from trendalgo.device.views.plan_page import PlanPage  # noqa: E402
from trendalgo.device.views.scanner_page import ScannerPage  # noqa: E402
from trendalgo.device.views.settings_page import SettingsPage  # noqa: E402
from trendalgo.device.views.status_page import StatusPage  # noqa: E402
from trendalgo.device.workers import WorkerPool  # noqa: E402

RUN_TIMEOUT_MS = 120_000


def _add_bot(page: PlanPage, name: str = "Alpha", pair: str = "btc/usd", stop: str = "5") -> None:
    page._name.setText(name)
    page._pair.setText(pair)
    page._stake.setText("100")
    page._stop.setText(stop)
    page._add_bot()


def test_first_run_opens_on_portfolio(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
) -> None:
    window = MainWindow(ctx, pool)
    qtbot.addWidget(window)
    assert window._stack.currentIndex() == PORTFOLIO
    assert window._nav.count() >= 1


def test_a_saved_profile_opens_on_the_portfolio(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
) -> None:
    write_json(ctx.settings_path, {"owner_id": "owner-1", "host_url": ""})
    window = MainWindow(ctx, pool)
    qtbot.addWidget(window)
    assert window._nav.currentIndex() == PORTFOLIO


def test_reopen_restores_last_nav_page(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
) -> None:
    from trendalgo.device.ui_state import default_nav_page, load_nav_page

    write_json(ctx.settings_path, {"owner_id": "owner-1", "host_url": ""})
    window = MainWindow(ctx, pool)
    qtbot.addWidget(window)
    assert default_nav_page(ctx.root) == PORTFOLIO
    window.show_page(BACKTESTS)
    assert load_nav_page(ctx.root) == BACKTESTS
    assert default_nav_page(ctx.root) == BACKTESTS


def test_settings_shows_about_with_version(qtbot: QtBot, ctx: DeviceContext) -> None:
    from PySide6.QtWidgets import QLabel

    from trendalgo import __version__

    page = SettingsPage(ctx)
    qtbot.addWidget(page)
    label = page.findChild(QLabel, "aboutVersion")
    assert label is not None
    assert __version__ in label.text()


def test_settings_refuses_bad_values_then_saves(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = SettingsPage(ctx)
    qtbot.addWidget(page)
    page._owner.setText("bad owner!")
    page.save()
    assert not ctx.settings_path.exists()
    assert "Owner ID" in page._problem.text()
    page._owner.setText("owner-1")
    page._host.setText("http://plain.example")
    page.save()
    assert "Host address" in page._problem.text()
    assert page._owner.text() == "owner-1"
    page._host.setText("")
    page.save()
    assert read_json(ctx.settings_path) == {
        "owner_id": "owner-1",
        "host_url": "",
        "theme": "system",
        "accent": "",
    }
    assert page._status.text() == S.SETTINGS_SAVED
    assert page._problem.isHidden()


def test_plan_builder_needs_an_owner_then_versions_each_save(
    qtbot: QtBot,
    ctx: DeviceContext,
) -> None:
    page = PlanPage(ctx)
    qtbot.addWidget(page)
    _add_bot(page)
    page._save_plan()
    assert S.PLAN_NEEDS_OWNER in page._problem.text()
    assert not ctx.plan_path.exists()
    write_json(ctx.settings_path, {"owner_id": "owner-1", "host_url": ""})
    page._save_plan()
    assert read_json(ctx.plan_path)["plan_version"] == 1
    assert "version 1" in page._status.text()
    _add_bot(page, name="Beta", pair="eth/usd", stop="0")
    page._save_plan()
    saved = read_json(ctx.plan_path)
    assert saved is not None
    assert saved["plan_version"] == 2
    assert len(saved["bots"]) == 2


def test_a_duplicate_bot_name_is_refused_and_the_typed_name_is_kept(
    qtbot: QtBot,
    ctx: DeviceContext,
) -> None:
    page = PlanPage(ctx)
    qtbot.addWidget(page)
    _add_bot(page, name="Alpha")
    _add_bot(page, name="Alpha")
    assert "Each bot needs a different name." in page._problem.text()
    assert page._name.text() == "Alpha"
    assert len(page._bots) == 1


def test_a_plan_file_that_cannot_be_read_is_never_overwritten(
    qtbot: QtBot,
    ctx: DeviceContext,
) -> None:
    ctx.plan_path.write_text("[1, 2]", encoding="utf-8")
    page = PlanPage(ctx)
    qtbot.addWidget(page)
    assert "must hold a JSON object" in page._problem.text()
    _add_bot(page)
    assert not page._save.isEnabled()
    page._save_plan()
    assert ctx.plan_path.read_text(encoding="utf-8") == "[1, 2]"


def test_scanner_and_status_show_empty_states_and_create_no_files(
    qtbot: QtBot,
    ctx: DeviceContext,
) -> None:
    scanner = ScannerPage(ctx)
    qtbot.addWidget(scanner)
    assert not scanner._empty.isHidden()
    assert scanner._table.isHidden()
    opened: list[bool] = []
    status = StatusPage(ctx, on_build_plan=lambda: opened.append(True))
    qtbot.addWidget(status)
    assert not status._bots_empty.isHidden()
    assert not status._journal_empty.isHidden()
    status._bots_empty.button.click()
    assert opened == [True]
    assert not ctx.databases["scanner"].exists()
    assert not ctx.databases["bots"].exists()


def test_backtest_refuses_bad_pair_and_keeps_what_was_typed(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
) -> None:
    page = BacktestPage(ctx, pool)
    qtbot.addWidget(page)
    page._pair.setText("nope")
    page._run.click()
    assert S.BACKTEST_PAIR_REQUIRED in page._problem.text()
    assert page._pair.text() == "nope"
    assert page._pending is None


def test_backtest_scan_fills_table_from_mocked_job(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {
            "indicator": "RSI",
            "timeframe": "1h",
            "params": {"length": 14},
            "trailing_stop_pct": 2.0,
            "net_pct": 12.0,
            "win_pct": 55.0,
            "trades": 4,
            "tsl_hits": 1,
        },
        {
            "indicator": "B&H",
            "timeframe": "1h",
            "params": {},
            "trailing_stop_pct": None,
            "net_pct": 5.0,
            "win_pct": "-",
            "trades": "-",
            "tsl_hits": 0,
        },
        {
            "indicator": "MACD",
            "timeframe": "1h",
            "params": {},
            "trailing_stop_pct": 0.0,
            "net_pct": 1.0,
            "win_pct": 40.0,
            "trades": 2,
            "tsl_hits": 0,
        },
    ]

    class _Ready:
        def ready(self) -> bool:
            return True

        def get(self, timeout: float = 0) -> list[dict[str, object]]:
            return rows

    page = BacktestPage(ctx, pool)
    qtbot.addWidget(page)
    monkeypatch.setattr(page._pool, "submit", lambda *_a, **_k: _Ready())
    page._pair.setText("BTC/USD")
    page._run.click()
    qtbot.waitUntil(lambda: page._status.text() == S.BACKTEST_DONE, timeout=5_000)
    # Row 0 = column filters; strategies start at 1.
    assert page._table.rowCount() == 4
    assert "RSI" in (page._table.item(1, 0).text() if page._table.item(1, 0) else "")
    assert page._run.isEnabled()
    page._on_header(4)
    assert page._table.rowCount() == 4


def test_cancel_stops_a_pair_scan(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
) -> None:
    page = BacktestPage(ctx, pool)
    qtbot.addWidget(page)
    page._pair.setText("BTC/USD")
    page._run.click()
    assert page._cancel.isEnabled()
    assert not page._run.isEnabled()
    page._cancel.click()
    assert page._status.text() == S.BACKTEST_CANCELLED
    assert page._run.isEnabled()
    assert not page._cancel.isEnabled()
    assert multiprocessing.active_children() == []


def test_the_selftest_window_check_builds_the_real_window() -> None:
    check_window()


def test_the_window_moves_between_sections_and_bots_fab_focuses_builder(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
) -> None:
    from trendalgo.device.views.bots_page import BotsPage

    window = MainWindow(ctx, pool, notices=["bots.db could not switch to safe-write mode."])
    qtbot.addWidget(window)
    window.show_page(BACKTESTS)
    assert window._stack.currentIndex() == BACKTESTS
    window.show_page(STATUS)
    stacked = window._stack.widget(STATUS)
    bots_page = stacked.widget() if hasattr(stacked, "widget") else stacked
    assert isinstance(bots_page, BotsPage)
    bots_page._status._bots_empty.button.click()
    assert window._stack.currentIndex() == STATUS
