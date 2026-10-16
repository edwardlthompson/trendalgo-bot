"""Per-column scanner filters installed as table row 0 (perfect column lock)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from trendalgo.device.views.scanner_table import COLUMNS

_CHART_OPTS = (("", "·"), ("5", "5%"), ("10", "10%"), ("15", "15%"))
_HEALTH_OPTS = (("", "·"), ("60", "60"), ("65", "65"), ("70", "70"))
_UNIT_OPTS = (("", "·"), ("20", "20"), ("30", "30"), ("40", "40"), ("50", "50"), ("60", "60"))
_VOL_ACCEL_OPTS = (("", "·"), ("pos", "+"), ("25", "25%"), ("50", "50%"))
_VOL24_OPTS = (
    ("", "·"),
    ("100000", "100k"),
    ("500000", "500k"),
    ("1000000", "1M"),
    ("10000000", "10M"),
)
# Bot better than B&H vs B&H better (buy-and-hold edge).
_BOT_VS_BH_OPTS = (("", "·"), ("pos", "Bot+"), ("neg", "B&H+"))
_DEFAULT_GAIN = 0
FILTER_ROW = 0
FILTER_ROW_PX = 28

_COL_GAIN7, _COL_SPARK7, _COL_GAIN30, _COL_SPARK30 = 4, 5, 6, 7
_COL_BEST, _COL_BOT_VS_BH = 8, 9
_COL_UNIT, _COL_HEALTH, _COL_VOL_ACCEL, _COL_VOL24 = 10, 11, 14, 16


class GainMinEdit(QLineEdit):
    """Plain int field for min gain %. Empty or 0 means no filter. Survives click-then-type."""

    def __init__(self, tip: str) -> None:
        super().__init__()
        self.setToolTip(tip)
        self.setPlaceholderText("min%")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setValidator(QIntValidator(0, 1000, self))
        self.setClearButtonEnabled(True)

    def value(self) -> int:
        text = self.text().strip()
        if not text:
            return 0
        try:
            return int(text)
        except ValueError:
            return 0

    def setValue(self, value: int) -> None:
        self.setText("" if int(value) <= 0 else str(int(value)))

    def interpretText(self) -> None:
        """Match QSpinBox API used by dump()."""
        self.setValue(self.value())

    def suffix(self) -> str:
        """Compat for older tests — display uses placeholder, not a suffix."""
        return "%"


class ScannerColumnFilterRow(QWidget):
    """Owns filter controls and mounts them into table row 0 after each fill."""

    def __init__(self) -> None:
        super().__init__()
        self.gain_7d = GainMinEdit("Min 7D % — empty or 0 shows all. Type e.g. 7 then Enter.")
        self.gain_30d = GainMinEdit("Min 30D % — empty or 0 shows all. Type e.g. 10 then Enter.")
        self.best_bt = GainMinEdit(
            "Min Best BT % — hide coins whose best bot result is below this."
        )
        self.bot_vs_bh = self._combo(
            _BOT_VS_BH_OPTS,
            tip="Bot+ = bot beat buy-and-hold. B&H+ = buy-and-hold beat the bot.",
        )
        self.chart_dist_7d = self._combo(_CHART_OPTS, tip="Max 7d chart dist from high")
        self.chart_dist_30d = self._combo(_CHART_OPTS, tip="Max 30d chart dist from high")
        self.health_min = self._combo(_HEALTH_OPTS, tip="Min health")
        self.uniformity_min = self._combo(_UNIT_OPTS, tip="Min uniformity")
        self.vol_accel = self._combo(_VOL_ACCEL_OPTS, tip="Volume acceleration")
        self.vol24_min = self._combo(_VOL24_OPTS, tip="Min 24h volume")
        self._by_col: dict[int, QWidget] = {
            _COL_GAIN7: self.gain_7d,
            _COL_SPARK7: self.chart_dist_7d,
            _COL_GAIN30: self.gain_30d,
            _COL_SPARK30: self.chart_dist_30d,
            _COL_BEST: self.best_bt,
            _COL_BOT_VS_BH: self.bot_vs_bh,
            _COL_UNIT: self.uniformity_min,
            _COL_HEALTH: self.health_min,
            _COL_VOL_ACCEL: self.vol_accel,
            _COL_VOL24: self.vol24_min,
        }
        self._table: QTableWidget | None = None
        self.hide()

    def attach(self, table: QTableWidget) -> None:
        self._table = table

    def prepare_for_refill(self) -> None:
        """Reparent controls onto self only when the filter row is about to be wiped."""
        for control in self._by_col.values():
            control.setParent(self)
            control.hide()

    def row_installed(self, table: QTableWidget) -> bool:
        host = table.cellWidget(FILTER_ROW, _COL_GAIN7)
        return host is not None and host.findChild(GainMinEdit) is self.gain_7d

    def install_row(self, table: QTableWidget) -> None:
        """Place compact controls in row 0; reuse hosts when already installed."""
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
            host.setObjectName("scannerFilterCell")
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
            width = max(table.columnWidth(column) - 4, 28)
            control.setMaximumWidth(width)

    def sync_geometry(self) -> None:
        if self._table is not None and self._table.rowCount() > 0:
            self.install_row(self._table)

    def sync_widths(self, table: QTableWidget) -> None:
        self.install_row(table)

    def set_filters_visible(self, visible: bool) -> None:
        table = self._table
        if table is None or table.rowCount() < 1:
            return
        table.setRowHidden(FILTER_ROW, not visible)

    def load(self, saved: dict[str, Any]) -> None:
        if "min_gain_7d" in saved:
            self.gain_7d.setValue(int(float(saved["min_gain_7d"])))
        else:
            self.gain_7d.setValue(_DEFAULT_GAIN)
        if "min_gain_30d" in saved:
            self.gain_30d.setValue(int(float(saved["min_gain_30d"])))
        elif "min_gain_pct" in saved:
            self.gain_30d.setValue(int(float(saved["min_gain_pct"])))
        else:
            self.gain_30d.setValue(_DEFAULT_GAIN)
        if "min_best_bt" in saved:
            self.best_bt.setValue(int(float(saved["min_best_bt"])))
        else:
            self.best_bt.setValue(_DEFAULT_GAIN)
        self._set(self.bot_vs_bh, saved.get("bot_vs_bh_filter"))
        self._set(self.chart_dist_7d, saved.get("chart_dist_max_7d"))
        self._set(self.chart_dist_30d, saved.get("chart_dist_max_30d"))
        self._set(self.health_min, saved.get("health_min"))
        self._set(self.uniformity_min, saved.get("uniformity_min"))
        self._set(self.vol_accel, saved.get("vol_accel_filter"))
        self._set(self.vol24_min, saved.get("vol24_min"))

    def dump(self) -> dict[str, Any]:
        self.gain_7d.interpretText()
        self.gain_30d.interpretText()
        self.best_bt.interpretText()
        return {
            "min_gain_7d": float(self.gain_7d.value()),
            "min_gain_30d": float(self.gain_30d.value()),
            "min_gain_pct": float(self.gain_30d.value()),
            "min_best_bt": float(self.best_bt.value()),
            "bot_vs_bh_filter": self._val(self.bot_vs_bh),
            "chart_dist_max_7d": self._val(self.chart_dist_7d),
            "chart_dist_max_30d": self._val(self.chart_dist_30d),
            "health_min": self._val(self.health_min),
            "uniformity_min": self._val(self.uniformity_min),
            "vol_accel_filter": self._val(self.vol_accel),
            "vol24_min": self._val(self.vol24_min),
        }

    @staticmethod
    def _combo(options: tuple[tuple[str, str], ...], *, tip: str) -> QComboBox:
        box = QComboBox()
        box.setToolTip(tip)
        box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        box.setMinimumContentsLength(0)
        for value, label in options:
            box.addItem(label, value)
        return box

    @staticmethod
    def _set(box: QComboBox, raw: object) -> None:
        text = "" if raw is None else str(raw)
        index = box.findData(text)
        box.setCurrentIndex(index if index >= 0 else 0)

    @staticmethod
    def _val(box: QComboBox) -> str:
        data = box.currentData()
        return str(data) if data is not None else ""
