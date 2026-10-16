"""Scan action strip: Exchange, min vol, interval, Color ranks, Run/Cancel."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QToolButton,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.icons import nav_icon
from trendalgo.device.lts_scan_model import EXCHANGES
from trendalgo.device.scanner_signal_sets import (
    BT_SET_3COMMAS,
    BT_SET_ALL_TA,
    normalize_bt_signal_set,
)
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.widgets import mark_primary

_DEFAULT_VOL = 0
_DEFAULT_UNIT = 0.20
_DEFAULT_EVERY = 60
_SIGNAL_ITEMS = (
    (S.SCANNER_SIGNALS_3COMMAS, BT_SET_3COMMAS),
    (S.SCANNER_SIGNALS_ALL_TA, BT_SET_ALL_TA),
)


class ScannerFilterBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.exchange = QComboBox()
        self.exchange.addItems(list(EXCHANGES))
        self.vol = QDoubleSpinBox()
        self.vol.setRange(0, 1e12)
        self.vol.setDecimals(0)
        self.vol.setPrefix("$")
        self.vol.setSingleStep(100_000)
        self.every = QSpinBox()
        self.every.setRange(60, 1440)
        self.every.setSuffix(" min")
        self.signals = QComboBox()
        for label, value in _SIGNAL_ITEMS:
            self.signals.addItem(label, value)
        # Tall enough that closed text + popup rows are not vertically clipped.
        _fm = self.signals.fontMetrics()
        _row_h = max(28, _fm.height() + 14)
        self.signals.setMinimumHeight(_row_h)
        self.signals.setMaxVisibleItems(len(_SIGNAL_ITEMS))
        self.signals.view().setMinimumHeight(_row_h * len(_SIGNAL_ITEMS) + 8)
        self.signals.setStyleSheet(
            f"QComboBox {{ min-height: {_row_h}px; padding-top: 4px; padding-bottom: 4px; }}"
            f"QComboBox QAbstractItemView::item {{ min-height: {_row_h}px; }}"
        )
        self.heatmap = QCheckBox(S.SCANNER_COLOR_RANKS)
        self.heatmap.setChecked(False)
        self.perfect = QCheckBox(S.BACKTEST_PERFECT_ONLY)
        self.perfect.setChecked(False)
        self.perfect.setToolTip(S.BACKTEST_PERFECT_HELP)
        self.run = mark_primary(QPushButton(S.SCAN_RUN))
        self.run.setDefault(True)
        self.cancel = QPushButton(S.CANCEL)
        self.cancel.setEnabled(False)
        self.compare_btn = QPushButton(S.SCANNER_COMPARE_BTN)
        self.clear_btn = QPushButton(S.SCANNER_COMPARE_CLEAR)
        self.share = QToolButton()
        self.share.setObjectName("shareButton")
        self.share.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.share.setIcon(nav_icon("share", colors_for(active_mode())["onSurfaceVariant"], 20))
        self.share.setToolTip(S.SCANNER_SHARE_TIP)
        self.share.setAccessibleName(S.SCANNER_SHARE)
        self.auto_status = QLabel()
        self.auto_status.setObjectName("hint")
        self.compare_label = QLabel(S.SCANNER_COMPARE_EMPTY)
        self.compare_label.setObjectName("hint")
        self._min_uniformity = _DEFAULT_UNIT
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        for label, widget in (
            (S.SCANNER_FILTER_EXCHANGE, self.exchange),
            (S.SCANNER_FILTER_VOL, self.vol),
            (S.SCANNER_FILTER_EVERY, self.every),
            (S.SCANNER_FILTER_SIGNALS, self.signals),
        ):
            row.addWidget(QLabel(label))
            row.addWidget(widget)
        row.addWidget(self.heatmap)
        row.addWidget(self.perfect)
        row.addWidget(self.run)
        row.addWidget(self.cancel)
        row.addWidget(self.compare_btn)
        row.addWidget(self.clear_btn)
        row.addWidget(self.share)
        row.addWidget(self.compare_label, 1)
        row.addWidget(self.auto_status)
        self.vol.setValue(_DEFAULT_VOL)
        self.every.setValue(_DEFAULT_EVERY)

    def set_compare_pairs(self, pairs: set[str]) -> None:
        if pairs:
            self.compare_label.setText(S.SCANNER_COMPARE.format(pairs=", ".join(sorted(pairs))))
        else:
            self.compare_label.setText(S.SCANNER_COMPARE_EMPTY)

    def load(self, saved: dict[str, Any]) -> None:
        exchange = str(saved.get("exchange", "All"))
        index = self.exchange.findText(exchange)
        self.exchange.setCurrentIndex(index if index >= 0 else 0)
        self.vol.setValue(int(float(saved.get("min_volume_usd", _DEFAULT_VOL))))
        self.every.setValue(int(saved.get("interval_minutes", _DEFAULT_EVERY)))
        self._min_uniformity = float(saved.get("min_uniformity", _DEFAULT_UNIT))
        self.heatmap.setChecked(bool(saved.get("heatmap_enabled", False)))
        self.perfect.setChecked(bool(saved.get("perfect_only", False)))
        signal_set = normalize_bt_signal_set(saved.get("bt_signal_set"))
        sig_index = self.signals.findData(signal_set)
        self.signals.setCurrentIndex(sig_index if sig_index >= 0 else 0)

    def dump(self) -> dict[str, Any]:
        self.vol.interpretText()
        self.every.interpretText()
        raw = self.signals.currentData()
        return {
            "exchange": self.exchange.currentText(),
            "min_volume_usd": float(self.vol.value()),
            "min_uniformity": float(self._min_uniformity),
            "interval_minutes": int(self.every.value()),
            "heatmap_enabled": bool(self.heatmap.isChecked()),
            "perfect_only": bool(self.perfect.isChecked()),
            "bt_signal_set": normalize_bt_signal_set(raw),
        }

    def set_running(self, running: bool) -> None:
        self.run.setEnabled(not running)
        self.cancel.setEnabled(running)
