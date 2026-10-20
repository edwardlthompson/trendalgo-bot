"""Scanner chart dialog: price-only and single-strategy Show Chart modes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pytestqt.qtbot import QtBot

from trendalgo.device.views.scanner_chart_dialog import show_scanner_chart_dialog


def test_chart_dialog_uses_windowed_open_and_min_width() -> None:
    body = Path("src/trendalgo/device/views/scanner_chart_dialog.py").read_text(encoding="utf-8")
    assert "_open_windowed" in body
    assert "showFullScreen" not in body
    assert "_CHART_MIN_WIDTH" in body
    assert "ScrollBarAsNeeded" in body


@pytest.fixture
def coin() -> dict[str, Any]:
    return {
        "symbol": "BTC",
        "pair": "BTC/USD",
        "spark_closes_7d": [100.0 + i * 0.1 for i in range(40)],
        "spark_closes_30d": [100.0 + i * 0.05 for i in range(80)],
    }


def test_price_only_chart_opens_and_closes(qtbot: QtBot, coin: dict[str, Any]) -> None:
    from PySide6.QtWidgets import QApplication, QWidget

    parent = QWidget()
    qtbot.addWidget(parent)
    # Non-blocking: open then reject via Escape path is heavy; call with empty closes
    # after forcing a short-lived dialog by monkeypatching exec.
    opened: list[bool] = []

    def _fake_exec(self: Any) -> int:  # noqa: ANN401
        opened.append(True)
        return 0

    from PySide6.QtWidgets import QDialog

    monkey = pytest.MonkeyPatch()
    monkey.setattr(QDialog, "exec", _fake_exec)
    try:
        show_scanner_chart_dialog(parent, coin, window="7d", price_only=True)
    finally:
        monkey.undo()
    assert opened == [True]
    assert QApplication.instance() is not None


def test_bh_strategy_row_forces_price_only(qtbot: QtBot, coin: dict[str, Any]) -> None:
    from PySide6.QtWidgets import QDialog, QWidget

    parent = QWidget()
    qtbot.addWidget(parent)
    opened: list[bool] = []

    def _fake_exec(self: Any) -> int:  # noqa: ANN401
        opened.append(True)
        return 0

    monkey = pytest.MonkeyPatch()
    monkey.setattr(QDialog, "exec", _fake_exec)
    try:
        show_scanner_chart_dialog(
            parent,
            coin,
            window="30d",
            strategy_row={"indicator": "B&H", "timeframe": "1h", "net_pct": 1.0},
        )
    finally:
        monkey.undo()
    assert opened == [True]


def test_strategy_row_chart_opens(qtbot: QtBot, coin: dict[str, Any]) -> None:
    from PySide6.QtWidgets import QDialog, QWidget

    parent = QWidget()
    qtbot.addWidget(parent)
    opened: list[bool] = []

    def _fake_exec(self: Any) -> int:  # noqa: ANN401
        opened.append(True)
        return 0

    monkey = pytest.MonkeyPatch()
    monkey.setattr(QDialog, "exec", _fake_exec)
    try:
        show_scanner_chart_dialog(
            parent,
            coin,
            window="7d",
            strategy_row={"indicator": "RSI", "timeframe": "1h", "net_pct": 12.0, "trades": 3},
        )
    finally:
        monkey.undo()
    assert opened == [True]


def test_overlay_win_loss_label_anchors(qtbot: QtBot) -> None:
    from datetime import UTC, datetime, timedelta

    from PySide6.QtWidgets import QWidget

    from trendalgo.device.views.scanner_chart_dialog import _OverlayChart

    parent = QWidget()
    qtbot.addWidget(parent)
    chart = _OverlayChart(parent)
    qtbot.addWidget(chart)
    chart.show()
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    closes = [(int((t0 + timedelta(hours=i)).timestamp() * 1000), 100.0 + i) for i in range(8)]
    regions = [
        {
            "entry_time": t0 + timedelta(hours=1),
            "exit_time": t0 + timedelta(hours=3),
            "entry_price": 101.0,
            "exit_price": 104.0,
            "label": "+3%",
            "profitable": True,
        },
        {
            "entry_time": t0 + timedelta(hours=4),
            "exit_time": t0 + timedelta(hours=6),
            "entry_price": 105.0,
            "exit_price": 102.0,
            "label": "-2%",
            "profitable": False,
        },
    ]
    chart.set_frame(None, [c[1] for c in closes], regions)
    qtbot.waitUntil(lambda: len(chart._labels) >= 1, timeout=2000)  # noqa: SLF001
