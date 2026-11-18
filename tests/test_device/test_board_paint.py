"""Viewport-lazy board enrich keeps the UI free."""

from __future__ import annotations

from typing import Any

import pytest


def test_board_paint_viewport_enrich(qtbot: Any, monkeypatch: Any) -> None:
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QProgressBar, QTabBar, QTableWidget

    from trendalgo.device import strings as S
    from trendalgo.device.views import board_paint as bp
    from trendalgo.device.views.board_paint import BoardPaintController
    from trendalgo.device.views.scanner_table import fill_lts_table

    calls: list[tuple[int, int]] = []

    def _fake_enrich(table: Any, coins: Any, *, start: int, end: int, **_k: Any) -> None:
        calls.append((start, end))

    monkeypatch.setattr(bp, "enrich_lts_rows", _fake_enrich)

    table = QTableWidget()
    tabs = QTabBar()
    tabs.addTab(S.SCANNER_TAB_QUALIFIED)
    progress = QProgressBar()
    coins = [
        {
            "symbol": f"S{i}",
            "pair": f"S{i}/USD",
            "name": f"S{i}",
            "gains": {"7d": 1.0, "30d": 2.0},
        }
        for i in range(40)
    ]
    fill_lts_table(
        table,
        coins,
        filter_row=False,
        include_widgets=False,
        include_sparks=False,
    )
    ctrl = BoardPaintController(
        table=table,
        tabs=tabs,
        progress=progress,
        status_set=lambda _t: None,
        desk_label="TradFi",
    )
    qtbot.addWidget(table)
    ctrl.start(coins, filter_row=False)
    for _ in range(10):
        ctrl._tick()  # noqa: SLF001
    assert calls  # at least one enrich chunk scheduled
    assert all(end - start == 1 for start, end in calls)
