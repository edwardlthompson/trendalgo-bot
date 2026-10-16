"""Fill the Backtest results table (data rows + Create Bot widgets)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.backtest_results_ui import (
    NET_COL,
    STRENGTH_COL,
    heat_for_rows,
    net_tooltip,
    row_cells,
    skip_tooltip,
)
from trendalgo.device.backtest_sort import COL_SORT_KEYS
from trendalgo.device.scanner_heat import fg_for_bg
from trendalgo.device.scanner_plan_prefill import plan_prefill_from_scanner_row
from trendalgo.device.scanner_sort import header_label
from trendalgo.device.table_fit import fit_table_columns
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.backtest_column_filter_row import BacktestColumnFilterRow
from trendalgo.device.views.glossary_popup import glossary_tooltip

_BH = "B&H"
CreateBotCb = Callable[[dict[str, str]], None]
NoteCb = Callable[[str], None]


def apply_headers(table: QTableWidget, *, sort_key: str, sort_dir: int) -> None:
    labels = [
        header_label(
            S.BACKTEST_RESULT_HEADERS[i],
            active=COL_SORT_KEYS.get(i) == sort_key,
            direction=sort_dir,
        )
        for i in range(len(S.BACKTEST_RESULT_HEADERS))
    ]
    table.setHorizontalHeaderLabels(labels)
    item = table.horizontalHeaderItem(STRENGTH_COL)
    if item is not None:
        item.setToolTip(S.BACKTEST_STRENGTH_HELP)


def fill_backtest_table(
    table: QTableWidget,
    rows: list[dict[str, Any]],
    *,
    pair: str,
    heatmap: bool,
    sort_key: str,
    sort_dir: int,
    filter_row: BacktestColumnFilterRow,
    on_open_plan: CreateBotCb | None,
    on_note: NoteCb,
) -> None:
    offset = 1
    filter_row.prepare_for_refill()
    while table.rowCount() > 1:
        table.removeRow(table.rowCount() - 1)
    table.setRowCount(len(rows) + offset)
    apply_headers(table, sort_key=sort_key, sort_dir=sort_dir)
    filter_row.install_row(table)
    theme = colors_for(active_mode())
    bh_bg = theme["secondaryContainer"]
    bh_fg = theme["onSecondaryContainer"]
    heat = heat_for_rows(rows) if heatmap else {}
    for r, row in enumerate(rows):
        row_i = r + offset
        is_bh = str(row.get("indicator") or "").strip() == _BH
        cells = row_cells(row, is_bh=is_bh)
        for c, text in enumerate(cells):
            item = QTableWidgetItem(text)
            if c == 0 and not is_bh:
                tip = glossary_tooltip(str(row.get("indicator") or ""))
                skip = skip_tooltip(row)
                if skip:
                    tip = f"{skip}\n\n{tip}" if tip else skip
                if tip:
                    item.setToolTip(tip)
                item.setData(Qt.ItemDataRole.UserRole, str(row.get("indicator") or ""))
                item.setForeground(QColor(theme["primary"]))
                font = item.font()
                font.setUnderline(True)
                item.setFont(font)
            if c == NET_COL and not is_bh:
                tip = net_tooltip(row, is_bh=False)
                if tip:
                    item.setToolTip(tip)
            if c == STRENGTH_COL and not is_bh:
                item.setToolTip(S.BACKTEST_STRENGTH_HELP)
            if is_bh:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setBackground(QColor(bh_bg))
                item.setForeground(QColor(bh_fg))
            elif c in heat:
                bg = heat[c][r] if r < len(heat[c]) else None
                if bg:
                    item.setBackground(QColor(bg))
                    item.setForeground(QColor(fg_for_bg(bg)))
            table.setItem(row_i, c, item)
        _create_bot_cell(
            table, row_i, row, is_bh=is_bh, pair=pair, on_open_plan=on_open_plan, on_note=on_note
        )
    fit_table_columns(table)
    filter_row.sync_control_widths(table)


def _create_bot_cell(
    table: QTableWidget,
    row_i: int,
    strategy: dict[str, Any],
    *,
    is_bh: bool,
    pair: str,
    on_open_plan: CreateBotCb | None,
    on_note: NoteCb,
) -> None:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(2, 2, 2, 2)
    if is_bh or on_open_plan is None:
        layout.addWidget(QLabel("—"))
    else:
        btn = QPushButton(S.SCANNER_CREATE_BOT)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        open_plan = on_open_plan

        def _create(_checked: bool = False, data: dict[str, Any] = strategy) -> None:
            fields, note = plan_prefill_from_scanner_row(data, pair=pair)
            if fields is None:
                on_note(note)
                return
            open_plan(fields)
            on_note(note or S.FLEET_CREATE_BOT_SENT)

        btn.clicked.connect(_create)
        layout.addWidget(btn)
    table.setCellWidget(row_i, len(S.BACKTEST_RESULT_HEADERS) - 1, host)
