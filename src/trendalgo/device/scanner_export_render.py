"""Offscreen Qt panel that paints the scanner list for PNG export (sparks + heat)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device.market_context_export_gfx import build_buy_picks_gfx_band
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.scanner_table import COL_RESULTS, COL_WATCH, fill_lts_table
from trendalgo.device.views.scanner_table_cells import COL_LOGO

_HIDE = (COL_WATCH, COL_RESULTS)


def build_scanner_export_panel(
    *,
    coins: list[dict[str, Any]],
    title: str,
    filter_line: str,
    heatmap: bool,
    sort_key: str,
    sort_dir: int,
    include_market_context: bool = True,
    icon_root: Path | None = None,
    lane: str = "crypto",
) -> QWidget:
    theme = colors_for(active_mode())
    panel = QWidget()
    panel.setObjectName("panel")
    panel.setStyleSheet(
        f"QWidget#panel {{ background: {theme['surface']}; color: {theme['onSurface']}; }}"
    )
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)
    head = QLabel(title)
    font = QFont(head.font())
    font.setBold(True)
    font.setPointSize(max(11, font.pointSize() + 1))
    head.setFont(font)
    layout.addWidget(head)
    filt = QLabel(filter_line)
    filt.setObjectName("hint")
    filt.setWordWrap(True)
    layout.addWidget(filt)
    if include_market_context:
        picks_band = build_buy_picks_gfx_band(coins)
        if picks_band is not None:
            layout.addWidget(picks_band)
    if icon_root is not None and (lane or "").strip().lower() == "tradfi":
        from trendalgo.device.lane_icons import prefetch_equity_logo

        for coin in coins:
            sym = str(coin.get("symbol") or "").strip()
            if sym:
                try:
                    prefetch_equity_logo(icon_root, sym)
                except Exception:  # noqa: BLE001 — export must not fail on one logo
                    continue
    table = QTableWidget()
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.verticalHeader().setVisible(False)
    fill_lts_table(
        table,
        coins,
        watch=set(),
        sort_key=sort_key,
        sort_dir=sort_dir,
        heatmap=heatmap,
        filter_row=False,
        icon_root=icon_root,
        lane=lane,
    )
    for col in _HIDE:
        table.setColumnHidden(col, True)
    table.resizeRowsToContents()
    table.resizeColumnsToContents()
    table.setColumnWidth(COL_LOGO, max(table.columnWidth(COL_LOGO), 52))
    _fit_table(table)
    layout.addWidget(table)
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    panel.setFixedWidth(max(table.width() + 24, panel.sizeHint().width()))
    panel.adjustSize()
    return panel


def _fit_table(table: QTableWidget) -> None:
    visible = [c for c in range(table.columnCount()) if not table.isColumnHidden(c)]
    width = sum(table.columnWidth(c) for c in visible) + 4
    height = table.horizontalHeader().height() + sum(
        table.rowHeight(r) for r in range(table.rowCount())
    )
    table.setFixedSize(width, height)
