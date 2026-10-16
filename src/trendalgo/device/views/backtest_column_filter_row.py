"""Per-column Backtest filters installed as table row 0."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from trendalgo.device import strings as S

FILTER_ROW = 0
FILTER_ROW_PX = 28
COLUMNS = len(S.BACKTEST_RESULT_HEADERS)


class _NumEdit(QLineEdit):
    """Optional int filter. Empty = inactive. clearButtonEnabled for quick reset."""

    def __init__(self, tip: str, *, placeholder: str, maximum: int = 10_000) -> None:
        super().__init__()
        self.setToolTip(tip)
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setValidator(QIntValidator(0, maximum, self))
        self.setClearButtonEnabled(True)

    def raw(self) -> str:
        return self.text().strip()

    def set_raw(self, value: object) -> None:
        if value in (None, "", "-"):
            self.clear()
            return
        self.setText(str(int(float(value))))  # type: ignore[arg-type]


class _TextEdit(QLineEdit):
    def __init__(self, tip: str, *, placeholder: str) -> None:
        super().__init__()
        self.setToolTip(tip)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)


class BacktestColumnFilterRow(QWidget):
    """Owns filter controls and mounts them into table row 0 after each fill."""

    def __init__(self) -> None:
        super().__init__()
        self.indicator = _TextEdit("Filter indicator name (contains)", placeholder="name")
        self.timeframe = _TextEdit("Exact timeframe, e.g. 1h", placeholder="tf")
        self.params = _TextEdit("Filter params text (contains)", placeholder="params")
        self.min_net = _NumEdit("Min Net %", placeholder="min%")
        self.max_fees = _NumEdit("Max fees $", placeholder="max$")
        self.max_open = _NumEdit(
            "Max open trades at end — type 0 for only fully closed strategies",
            placeholder="max",
        )
        self.min_wins = _NumEdit("Min winning trades", placeholder="min")
        self.max_losses = _NumEdit("Max losing trades", placeholder="max")
        self.min_win = _NumEdit("Min Win %", placeholder="min%")
        self.max_tsl = _NumEdit("Max TSL %", placeholder="max%")
        self.max_hits = _NumEdit(
            "Max TSL Hits — type 0 to show only zero-hit strategies",
            placeholder="max",
        )
        self.max_hit_pct = _NumEdit("Max TSL Hit %", placeholder="max%")
        self.min_strength = _NumEdit("Min Strength 0–100", placeholder="min", maximum=100)
        self._by_col: dict[int, QWidget] = {
            0: self.indicator,
            1: self.timeframe,
            2: self.params,
            3: self.min_net,
            4: self.max_fees,
            5: self.max_open,
            6: self.min_wins,
            7: self.max_losses,
            8: self.min_win,
            9: self.max_tsl,
            10: self.max_hits,
            11: self.max_hit_pct,
            12: self.min_strength,
        }
        self._table: QTableWidget | None = None
        self.hide()

    def attach(self, table: QTableWidget) -> None:
        self._table = table

    def prepare_for_refill(self) -> None:
        for control in self._by_col.values():
            control.setParent(self)
            control.hide()

    def row_installed(self, table: QTableWidget) -> bool:
        host = table.cellWidget(FILTER_ROW, 0)
        return host is not None and host.findChild(_TextEdit) is self.indicator

    def install_row(self, table: QTableWidget) -> None:
        self._table = table
        if table.rowCount() < 1:
            table.setRowCount(1)
        table.setRowHeight(FILTER_ROW, FILTER_ROW_PX)
        marker = QTableWidgetItem("⌕")
        marker.setFlags(Qt.ItemFlag.NoItemFlags)
        marker.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setVerticalHeaderItem(FILTER_ROW, marker)
        if self.row_installed(table):
            self.sync_control_widths(table)
            return
        for column in range(COLUMNS):
            control = self._by_col.get(column)
            if control is None:
                blank = QTableWidgetItem("")
                blank.setFlags(Qt.ItemFlag.NoItemFlags)
                table.setItem(FILTER_ROW, column, blank)
                continue
            host = QWidget()
            host.setObjectName("backtestFilterCell")
            layout = QHBoxLayout(host)
            layout.setContentsMargins(1, 1, 1, 1)
            layout.setSpacing(0)
            control.setParent(host)
            control.setMaximumHeight(FILTER_ROW_PX - 2)
            control.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            control.show()
            layout.addWidget(control)
            table.setCellWidget(FILTER_ROW, column, host)
        table.verticalHeader().setSectionResizeMode(FILTER_ROW, QHeaderView.ResizeMode.Fixed)
        self.sync_control_widths(table)

    def sync_control_widths(self, table: QTableWidget) -> None:
        for column, control in self._by_col.items():
            control.setMaximumWidth(max(table.columnWidth(column) - 4, 28))

    def dump(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.indicator.text().strip():
            out["indicator_contains"] = self.indicator.text().strip()
        if self.timeframe.text().strip():
            out["timeframe"] = self.timeframe.text().strip()
        if self.params.text().strip():
            out["params_contains"] = self.params.text().strip()
        self._put_min(out, "min_net_pct", self.min_net)
        self._put_max(out, "max_fees", self.max_fees, allow_zero=False)
        self._put_max(out, "max_open", self.max_open, allow_zero=True)
        self._put_min(out, "min_wins", self.min_wins)
        self._put_max(out, "max_losses", self.max_losses, allow_zero=True)
        self._put_min(out, "min_win_pct", self.min_win)
        self._put_max(out, "max_tsl_pct", self.max_tsl, allow_zero=False)
        self._put_max(out, "max_tsl_hits", self.max_hits, allow_zero=True)
        self._put_max(out, "max_tsl_hit_pct", self.max_hit_pct, allow_zero=False)
        self._put_min(out, "min_strength", self.min_strength)
        return out

    @staticmethod
    def _put_min(out: dict[str, Any], key: str, edit: _NumEdit) -> None:
        text = edit.raw()
        if not text:
            return
        value = int(text)
        if value > 0:
            out[key] = value

    @staticmethod
    def _put_max(out: dict[str, Any], key: str, edit: _NumEdit, *, allow_zero: bool) -> None:
        text = edit.raw()
        if not text:
            return
        value = int(text)
        if value > 0 or (allow_zero and value == 0):
            out[key] = value
