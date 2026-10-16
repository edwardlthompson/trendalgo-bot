"""Column filters wait 2s before applying so multi-digit entry is not mid-applied."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.views.backtest_page import FILTER_DEBOUNCE_MS, BacktestPage  # noqa: E402
from trendalgo.device.workers import WorkerPool  # noqa: E402


def test_filter_digits_debounce_before_refresh(
    qtbot: QtBot, ctx: DeviceContext, pool: WorkerPool
) -> None:
    page = BacktestPage(ctx, pool)
    qtbot.addWidget(page)
    page._all_rows = [
        {"indicator": "A", "trades": 10, "wins": 8, "win_pct": 80, "net_pct": 5},
        {"indicator": "B", "trades": 10, "wins": 2, "win_pct": 20, "net_pct": 1},
    ]
    page._rows = list(page._all_rows)
    calls: list[int] = []
    page._refresh_rows = lambda: calls.append(1)  # type: ignore[method-assign]
    page._filters.min_wins.setText("1")
    assert calls == []
    page._filters.min_wins.setText("12")
    assert calls == []
    qtbot.wait(FILTER_DEBOUNCE_MS + 200)
    assert calls == [1]
