"""Offscreen Qt panel that paints filtered Backtest rows for PNG export."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.backtest_results_ui import heat_for_rows, row_cells
from trendalgo.device.backtest_sort import COL_SORT_KEYS
from trendalgo.device.scanner_heat import fg_for_bg
from trendalgo.device.scanner_sort import header_label
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for

_BH = "B&H"
_EXPORT_COLS = len(S.BACKTEST_RESULT_HEADERS) - 1


def build_export_panel(
    *,
    pair: str,
    rows: list[dict[str, Any]],
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
    title = QLabel(f"{pair} · {len(rows)} strategies")
    title_font = QFont(title.font())
    title_font.setBold(True)
    title_font.setPointSize(max(11, title_font.pointSize() + 1))
    title.setFont(title_font)
    layout.addWidget(title)
    filt = QLabel(filter_line)
    filt.setObjectName("hint")
    filt.setWordWrap(True)
    layout.addWidget(filt)
    table = _filled_table(rows, heatmap=heatmap, sort_key=sort_key, sort_dir=sort_dir, theme=theme)
    layout.addWidget(table)
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    panel.setFixedWidth(max(table.width() + 24, panel.sizeHint().width()))
    panel.adjustSize()
    return panel


def _filled_table(
    rows: list[dict[str, Any]],
    *,
    heatmap: bool,
    sort_key: str,
    sort_dir: int,
    theme: dict[str, str],
) -> QTableWidget:
    table = QTableWidget(len(rows), _EXPORT_COLS)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.verticalHeader().setVisible(False)
    table.setHorizontalHeaderLabels(
        [
            header_label(
                S.BACKTEST_RESULT_HEADERS[i],
                active=sort_key == COL_SORT_KEYS.get(i, ""),
                direction=sort_dir,
            )
            for i in range(_EXPORT_COLS)
        ]
    )
    heat = heat_for_rows(rows) if heatmap else {}
    bh_bg, bh_fg = theme["secondaryContainer"], theme["onSecondaryContainer"]
    for r, row in enumerate(rows):
        is_bh = str(row.get("indicator") or "").strip() == _BH
        for c, text in enumerate(row_cells(row, is_bh=is_bh)[:_EXPORT_COLS]):
            item = QTableWidgetItem(text)
            if is_bh:
                item.setBackground(QColor(bh_bg))
                item.setForeground(QColor(bh_fg))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            elif c in heat:
                bg = heat[c][r] if r < len(heat[c]) else None
                if bg:
                    item.setBackground(QColor(bg))
                    item.setForeground(QColor(fg_for_bg(bg)))
            table.setItem(r, c, item)
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.resizeColumnsToContents()
    table.resizeRowsToContents()
    width = sum(table.columnWidth(c) for c in range(_EXPORT_COLS)) + 4
    height = table.horizontalHeader().height() + sum(
        table.rowHeight(r) for r in range(table.rowCount())
    )
    table.setFixedSize(width, height)
    return table
