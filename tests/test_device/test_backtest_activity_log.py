"""Backtest page polls progress into the status line (no activity panel)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.pair_scan_progress import write_progress  # noqa: E402
from trendalgo.device.views.backtest_page import BacktestPage  # noqa: E402
from trendalgo.device.workers import WorkerPool  # noqa: E402


def test_poll_updates_status_line(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Pending:
        def ready(self) -> bool:
            return False

    page = BacktestPage(ctx, pool)
    qtbot.addWidget(page)
    assert not hasattr(page, "_activity")
    monkeypatch.setattr(page._pool, "submit", lambda *_a, **_k: _Pending())
    page._pair.setText("ETH/USD")
    page._run.click()
    write_progress(ctx.root, {"message": "Loading ETH 1h…", "done": 0, "total": 10})
    page._poll()
    assert "Loading ETH 1h…" in page._status.text()
    page._cancel_run()
