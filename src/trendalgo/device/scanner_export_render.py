"""Offscreen Qt panel that paints the scanner list for PNG export (sparks + heat)."""

from __future__ import annotations

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

from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.scanner_table import COL_CMP, COL_RESULTS, COL_WATCH, fill_lts_table
from trendalgo.device.views.scanner_table_cells import COL_LOGO

_HIDE = (COL_WATCH, COL_CMP, COL_RESULTS)


def build_scanner_export_panel(
    *,
    coins: list[dict[str, Any]],
    title: str,
    filter_line: str,
    heatmap: bool,
    sort_key: str,
    sort_dir: int,
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
    table = QTableWidget()
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.verticalHeader().setVisible(False)
    fill_lts_table(
        table,
        coins,
        compare=set(),
        watch=set(),
        sort_key=sort_key,
        sort_dir=sort_dir,
        heatmap=heatmap,
        filter_row=False,
    )
    for col in _HIDE:
        table.setColumnHidden(col, True)
    table.resizeRowsToContents()
    table.resizeColumnsToContents()
    # Keep logo readable after resize-to-contents.
    table.setColumnWidth(COL_LOGO, max(table.columnWidth(COL_LOGO), 52))
    visible = [c for c in range(table.columnCount()) if not table.isColumnHidden(c)]
    width = sum(table.columnWidth(c) for c in visible) + 4
    height = table.horizontalHeader().height() + sum(
        table.rowHeight(r) for r in range(table.rowCount())
    )
    table.setFixedSize(width, height)
    layout.addWidget(table)
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    panel.setFixedWidth(max(width + 24, panel.sizeHint().width()))
    panel.adjustSize()
    return panel
