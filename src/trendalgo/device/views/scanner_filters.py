"""Scan action strip: Exchange checklist, min vol, interval, Color ranks, Settings, Run/Cancel."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QToolButton,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.flow_layout import FlowLayout
from trendalgo.device.icons import nav_icon
from trendalgo.device.scan_venues import vaulted_scan_venues
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.exchange_checklist import ExchangeChecklist
from trendalgo.device.views.widgets import mark_primary

_DEFAULT_VOL = 0
_DEFAULT_UNIT = 0.20
_DEFAULT_EVERY = 60


class ScannerFilterBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.exchange = ExchangeChecklist()
        self.refresh_exchange_options()
        self.vol = QDoubleSpinBox()
        self.vol.setRange(0, 1e12)
        self.vol.setDecimals(0)
        self.vol.setPrefix("$")
        self.vol.setSingleStep(100_000)
        self.every = QSpinBox()
        self.every.setRange(60, 1440)
        self.every.setSuffix(" min")
        self.heatmap = QCheckBox(S.SCANNER_COLOR_RANKS)
        self.heatmap.setChecked(False)
        self.settings = QToolButton()
        self.settings.setObjectName("scanBtSettings")
        self.settings.setText(S.SCAN_BT_SETTINGS)
        self.settings.setToolTip(S.SCAN_BT_SETTINGS_TIP)
        self.settings.setAccessibleName(S.SCAN_BT_SETTINGS)
        self.run = mark_primary(QPushButton(S.SCAN_RUN))
        self.run.setDefault(True)
        self.cancel = QPushButton(S.CANCEL)
        self.cancel.setEnabled(False)
        self.share = QToolButton()
        self.share.setObjectName("shareButton")
        self.share.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.share.setIcon(nav_icon("share", colors_for(active_mode())["onSurfaceVariant"], 20))
        self.share.setToolTip(S.SCANNER_SHARE_TIP)
        self.share.setAccessibleName(S.SCANNER_SHARE)
        self.auto_status = QLabel()
        self.auto_status.setObjectName("hint")
        self._min_uniformity = _DEFAULT_UNIT
        self.auto_status.setWordWrap(True)
        self.eta = QLabel()
        self.eta.setObjectName("hint")
        row = FlowLayout(self, margin=0, h_spacing=8, v_spacing=4)
        for label, widget in (
            (S.SCANNER_FILTER_EXCHANGE, self.exchange),
            (S.SCANNER_FILTER_VOL, self.vol),
            (S.SCANNER_FILTER_EVERY, self.every),
        ):
            row.addWidget(QLabel(label))
            row.addWidget(widget)
        row.addWidget(self.heatmap)
        row.addWidget(self.settings)
        row.addWidget(self.run)
        row.addWidget(self.cancel)
        row.addWidget(self.share)
        row.addWidget(self.auto_status)
        row.addWidget(self.eta)
        self.vol.setValue(_DEFAULT_VOL)
        self.every.setValue(_DEFAULT_EVERY)

    def refresh_exchange_options(self, selected: list[str] | None = None) -> None:
        venues = vaulted_scan_venues()
        opts = [(v.exchange_id, v.brand) for v in venues]
        self.exchange.set_options(opts, selected=selected)

    def load(self, saved: dict[str, Any]) -> None:
        raw = saved.get("scan_exchanges")
        selected = [str(x) for x in raw] if isinstance(raw, list) else None
        self.refresh_exchange_options(selected=selected)
        self.vol.setValue(int(self._num(saved.get("min_volume_usd"), _DEFAULT_VOL)))
        self.every.setValue(int(self._num(saved.get("interval_minutes"), _DEFAULT_EVERY)))
        self._min_uniformity = self._num(saved.get("min_uniformity"), _DEFAULT_UNIT)
        self.heatmap.setChecked(bool(saved.get("heatmap_enabled", False)))

    @staticmethod
    def _num(raw: object, default: float) -> float:
        """Prefs may store explicit null; ``dict.get`` then returns None, not the default."""
        if raw is None or raw == "":
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    def dump(self) -> dict[str, Any]:
        self.vol.interpretText()
        self.every.interpretText()
        selected = self.exchange.selected_ids()
        return {
            "exchange": "All",
            "scan_exchanges": selected,
            "min_volume_usd": float(self.vol.value()),
            "min_uniformity": float(self._min_uniformity),
            "interval_minutes": int(self.every.value()),
            "heatmap_enabled": bool(self.heatmap.isChecked()),
        }

    def set_running(self, running: bool) -> None:
        self.run.setEnabled(not running)
        self.cancel.setEnabled(running)
