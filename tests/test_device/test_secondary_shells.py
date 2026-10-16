"""Qt smoke for Export, Research, Debug, and Billing under More."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QPushButton  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.profile import DEVICE_LOG  # noqa: E402
from trendalgo.device.views.billing_page import BillingPage  # noqa: E402
from trendalgo.device.views.debug_page import DebugPage  # noqa: E402
from trendalgo.device.views.export_page import ExportPage  # noqa: E402
from trendalgo.device.views.main_window import EXPORT, MainWindow  # noqa: E402
from trendalgo.device.workers import WorkerPool  # noqa: E402
from trendalgo.risk.journal import TradeJournal, TradeRecord  # noqa: E402
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot  # noqa: E402
from trendalgo.scanner.store import ScannerStore  # noqa: E402


def test_more_menu_excludes_research_and_ai(
    qtbot: QtBot, ctx: DeviceContext, pool: WorkerPool
) -> None:
    window = MainWindow(ctx, pool)
    qtbot.addWidget(window)
    window.resize(320, 720)
    window._navbar.setFixedWidth(260)
    window._rebuild_nav(force=True)
    labels = {action.text() for action in window._menu.actions()}
    tab_labels = {window._nav.tabText(i) for i in range(window._nav.count())}
    all_labels = labels | tab_labels
    assert S.NAV_RESEARCH not in all_labels
    assert S.NAV_AI not in all_labels
    assert S.NAV_PLAN not in all_labels
    assert S.NAV_EXPORT in all_labels or S.NAV_GLOSSARY in all_labels


def test_export_page_writes_journal(
    qtbot: QtBot, ctx: DeviceContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = TradeJournal(ctx.databases["journal"])
    journal.append_trade(
        TradeRecord("BTC/USD", "long", 50.0, 1.0, "bot", "t", "id-1"),
        created_at="2026-10-10T12:00:00+00:00",
    )
    dest = tmp_path / "out"
    page = ExportPage(ctx)
    qtbot.addWidget(page)
    page._dest = dest
    page._refresh_folder_label()
    qtbot.mouseClick(page._journal, Qt.MouseButton.LeftButton)
    assert (dest / "journal-trades.csv").is_file()


def test_debug_page_shows_log_tail(qtbot: QtBot, ctx: DeviceContext) -> None:
    log = ctx.root / DEVICE_LOG
    log.write_text("alpha\nbeta\n", encoding="utf-8")
    page = DebugPage(ctx)
    qtbot.addWidget(page)
    assert "beta" in page._log.toPlainText()
    assert page._empty.isHidden()


def test_billing_settlement_and_referrals_disabled(qtbot: QtBot) -> None:
    page = BillingPage()
    qtbot.addWidget(page)
    pushes = page.findChildren(QPushButton)
    settle = next(btn for btn in pushes if btn.text() == S.BILLING_SETTLEMENT)
    referrals = next(btn for btn in pushes if btn.text() == S.BILLING_REFERRALS)
    assert not settle.isEnabled()
    assert not referrals.isEnabled()


def test_export_stack_page_index(qtbot: QtBot, ctx: DeviceContext, pool: WorkerPool) -> None:
    window = MainWindow(ctx, pool)
    qtbot.addWidget(window)
    window.show_page(EXPORT)
    assert isinstance(window._stack.currentWidget(), ExportPage)


def _seed_scan(ctx: DeviceContext) -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    snap = QualifiedSnapshot(
        generated_at=now,
        as_of=now,
        scan_id=3,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="ETH/USD",
                uniformity=0.5,
                gain_pct=2.0,
                volume_score=1.0,
                entry_signal=False,
            )
        ],
    )
    ScannerStore(ctx.databases["scanner"]).save_snapshot(snap)


def test_export_scan_shows_status(qtbot: QtBot, ctx: DeviceContext, tmp_path: Path) -> None:
    _seed_scan(ctx)
    page = ExportPage(ctx)
    qtbot.addWidget(page)
    page._dest = tmp_path / "exports"
    page._export_scan()
    assert "scan-latest.json" in page._status.text()
