"""Fill Scanner Results strategy table (optional filter row + data rows)."""

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
    CREATE_BOT_COL,
    SHOW_CHART_COL,
    heat_for_rows,
    row_cells,
    skip_tooltip,
)
from trendalgo.device.scanner_heat import fg_for_bg
from trendalgo.device.scanner_plan_prefill import plan_prefill_from_scanner_row
from trendalgo.device.table_fit import fit_table_columns
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.backtest_column_filter_row import FILTER_ROW, BacktestColumnFilterRow
from trendalgo.device.views.glossary_popup import glossary_tooltip

_BH = "B&H"
CreateBotCb = Callable[[dict[str, str], str], str]


def populate_results_table(
    table: QTableWidget,
    rows: list[dict[str, Any]],
    *,
    coin: dict[str, Any],
    pair: str,
    heatmap: bool,
    status: QLabel,
    parent: QWidget,
    filter_row: BacktestColumnFilterRow | None,
    on_create_bot: CreateBotCb | None,
    indicator_label: Callable[..., str],
) -> None:
    """Rewrite data rows; keep filter controls in row 0 when filter_row is set."""
    offset = 1 if filter_row is not None else 0
    if filter_row is not None:
        filter_row.prepare_for_refill()
        while table.rowCount() > 1:
            table.removeRow(table.rowCount() - 1)
        table.setRowCount(len(rows) + offset)
        filter_row.install_row(table)
    else:
        table.setRowCount(len(rows))
    theme = colors_for(active_mode())
    bh_bg = theme["secondaryContainer"]
    bh_fg = theme["onSecondaryContainer"]
    ss_bg = theme["primaryContainer"]
    ss_fg = theme["onPrimaryContainer"]
    heat = heat_for_rows(rows) if heatmap else {}
    signal_set = str(coin.get("bt_signal_set") or "")
    for r, row in enumerate(rows):
        row_i = r + offset
        name = str(row.get("indicator") or "").strip()
        is_bh = name == _BH
        from trendalgo.device.sauce_names import is_sauce as _is_sauce

        is_sauce = _is_sauce(name)
        is_baseline = name in {_BH, "Oracle max"}
        values = row_cells(row, is_bh=is_bh)
        for c, text in enumerate(values):
            label = indicator_label(name, bt_signal_set=signal_set, is_bh=is_bh) if c == 0 else text
            item = QTableWidgetItem(label)
            if c == 0 and not is_bh:
                if is_sauce:
                    tip = S.SECRET_SAUCE_FORMULA
                    dossier = row.get("heartbeat_dossier")
                    if isinstance(dossier, dict) and dossier.get("formula_en"):
                        tip = str(dossier.get("formula_en"))
                else:
                    tip = glossary_tooltip(name)
                    skip = skip_tooltip(row)
                    if skip:
                        tip = f"{skip}\n\n{tip}" if tip else skip
                if tip:
                    item.setToolTip(tip)
                item.setData(Qt.ItemDataRole.UserRole, name)
                item.setData(Qt.ItemDataRole.UserRole + 1, r)
                item.setForeground(QColor(theme["primary"]))
                font = item.font()
                font.setUnderline(True)
                item.setFont(font)
            if is_baseline or is_sauce:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            color = heat.get(c, [None] * len(rows))[r] if heatmap else None
            if color:
                item.setBackground(QColor(color))
                item.setForeground(QColor(fg_for_bg(color)))
            elif is_bh:
                item.setBackground(QColor(bh_bg))
                item.setForeground(QColor(bh_fg))
            elif is_sauce:
                item.setBackground(QColor(ss_bg))
                item.setForeground(QColor(ss_fg))
            table.setItem(row_i, c, item)
        _show_chart_cell(table, row_i, row, coin=coin, parent=parent)
        _create_bot_cell(
            table,
            row_i,
            row,
            is_bh=is_bh and not is_sauce,
            pair=pair,
            status=status,
            on_create_bot=on_create_bot,
        )
    fit_table_columns(table)
    if filter_row is not None:
        filter_row.sync_control_widths(table)


def data_row_index(table_row: int, *, has_filter_row: bool) -> int:
    return table_row - (FILTER_ROW + 1) if has_filter_row else table_row


def _show_chart_cell(
    table: QTableWidget,
    row: int,
    strategy: dict[str, Any],
    *,
    coin: dict[str, Any],
    parent: QWidget,
) -> None:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(2, 2, 2, 2)
    btn = QPushButton(S.BACKTEST_SHOW_CHART)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    name = str(strategy.get("indicator") or "").strip()
    from trendalgo.device.sauce_names import is_sauce_lab

    pending = is_sauce_lab(name) and bool(strategy.get("ss_lab_pending"))
    btn.setEnabled(not pending)

    def _open(_checked: bool = False, data: dict[str, Any] = strategy) -> None:
        from trendalgo.device.views.scanner_chart_dialog import show_scanner_chart_dialog

        show_scanner_chart_dialog(
            parent,
            coin,
            window="30d",
            price_only=str(data.get("indicator") or "").strip() == _BH,
            strategy_row=None if str(data.get("indicator") or "").strip() == _BH else data,
        )

    btn.clicked.connect(_open)
    layout.addWidget(btn)
    table.setCellWidget(row, SHOW_CHART_COL, host)


def _create_bot_cell(
    table: QTableWidget,
    row: int,
    strategy: dict[str, Any],
    *,
    is_bh: bool,
    pair: str,
    status: QLabel,
    on_create_bot: CreateBotCb | None,
) -> None:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(2, 2, 2, 2)
    if is_bh or on_create_bot is None:
        layout.addWidget(QLabel("—"))
    else:
        btn = QPushButton(S.SCANNER_CREATE_BOT)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        def _create(_checked: bool = False, row_data: dict[str, Any] = strategy) -> None:
            fields, note = plan_prefill_from_scanner_row(row_data, pair=pair)
            if fields is None:
                status.setText(note)
                return
            message = on_create_bot(fields, note)
            if message:
                status.setText(message)
            elif note:
                status.setText(note)

        btn.clicked.connect(_create)
        layout.addWidget(btn)
    table.setCellWidget(row, CREATE_BOT_COL, host)
