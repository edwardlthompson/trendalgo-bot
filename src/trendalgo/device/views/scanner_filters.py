"""Scan action strip: Run/Cancel + secondary buttons; board filters live in Settings."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.flow_layout import FlowLayout
from trendalgo.device.scan_venues import vaulted_scan_venues
from trendalgo.device.support_matrix import checklist_brand
from trendalgo.device.views.exchange_checklist import ExchangeChecklist
from trendalgo.device.views.widgets import mark_primary

_DEFAULT_VOL = 0
_DEFAULT_UNIT = 0.20
_DEFAULT_EVERY = 60


class ScannerFilterBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        # Prefs / Settings sync only — not on the strip.
        self.exchange = ExchangeChecklist()
        self.exchange.setToolTip(S.SCANNER_RESEARCH_HINT)
        self.exchange.setParent(self)
        self.exchange.hide()
        self.refresh_exchange_options()
        self.vol = QDoubleSpinBox()
        self.vol.setRange(0, 1e12)
        self.vol.setDecimals(0)
        self.vol.setPrefix("$")
        self.vol.setSingleStep(100_000)
        self.vol.setParent(self)
        self.vol.hide()
        self.every = QSpinBox()
        self.every.setRange(60, 1440)
        self.every.setSuffix(" min")
        self.every.setParent(self)
        self.every.hide()
        self.heatmap = QCheckBox(S.SCANNER_COLOR_RANKS)
        self.heatmap.setChecked(False)
        self.heatmap.setParent(self)
        self.heatmap.hide()

        self.settings = QPushButton(S.SCAN_BT_SETTINGS)
        self.settings.setObjectName("scanBtSettings")
        self.settings.setToolTip(S.SCAN_BT_SETTINGS_TIP)
        self.settings.setAccessibleName(S.SCAN_BT_SETTINGS)
        self.settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run = mark_primary(QPushButton(S.SCAN_RUN))
        self.run.setDefault(True)
        self.cancel = QPushButton(S.CANCEL)
        self.cancel.setEnabled(False)
        self.sauce_pan = QPushButton(S.SAUCE_PAN_RUN)
        self.sauce_pan.setObjectName("saucePanRun")
        self.sauce_pan.setToolTip(S.SAUCE_PAN_RUN_TIP)
        self.sauce_pan.setAccessibleName(S.SAUCE_PAN_TITLE)
        self.pool_watch = QPushButton(S.DEX_WATCH_RUN)
        self.pool_watch.setObjectName("dexWatchRun")
        self.pool_watch.setToolTip(S.DEX_WATCH_HINT)
        self.refresh_prices = QPushButton(S.SCAN_REFRESH_PRICES)
        self.refresh_prices.setToolTip(S.SCAN_REFRESH_PRICES_TIP)
        self.share = QPushButton(S.SCANNER_SHARE)
        self.share.setObjectName("shareButton")
        self.share.setToolTip(S.SCANNER_SHARE_TIP)
        self.share.setAccessibleName(S.SCANNER_SHARE)
        self.status_btn = QPushButton(S.SCANNER_STATUS)
        self.status_btn.setObjectName("scannerStatus")
        self.status_btn.setToolTip(S.SCANNER_STATUS_TIP)
        self.force_fresh = QPushButton(S.SCAN_FORCE_FRESH_DEBUG)
        self.force_fresh.setToolTip(S.SCAN_FORCE_FRESH_TIP)
        self.force_fresh.setVisible(False)

        self._eta_part = ""
        self._auto_part = ""
        self.auto_status = QLabel()
        self.auto_status.hide()
        self.eta = _EtaProxy(self)
        self._min_uniformity = _DEFAULT_UNIT
        self.research_hint = QLabel(S.SCANNER_RESEARCH_HINT)
        self.research_hint.hide()
        # Compat stub — strip no longer uses a More menu.
        self.more = QWidget()
        self.more.hide()

        strip = QWidget()
        row = FlowLayout(strip, margin=0, h_spacing=8, v_spacing=4)
        for btn in (
            self.run,
            self.cancel,
            self.settings,
            self.sauce_pan,
            self.pool_watch,
            self.refresh_prices,
            self.share,
            self.status_btn,
            self.force_fresh,
        ):
            row.addWidget(btn)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(strip)
        self.vol.setValue(_DEFAULT_VOL)
        self.every.setValue(_DEFAULT_EVERY)

    def status_text(self) -> str:
        bits = [S.SCANNER_STATUS_EVERY.format(minutes=int(self.every.value()))]
        if self._eta_part:
            bits.append(self._eta_part)
        if self._auto_part:
            bits.append(self._auto_part)
        return " · ".join(bits)

    def set_force_fresh_in_more(self, enabled: bool) -> None:
        self.force_fresh.setVisible(bool(enabled))

    def set_auto_status_text(self, text: str) -> None:
        self._auto_part = str(text or "").strip()
        self.auto_status.setText(self.status_text())

    def set_eta_text(self, text: str) -> None:
        self._eta_part = str(text or "").strip()
        self.auto_status.setText(self.status_text())

    def refresh_compact_status(self) -> None:
        self.auto_status.setText(self.status_text())

    def refresh_exchange_options(self, selected: list[str] | None = None) -> None:
        venues = vaulted_scan_venues()
        opts = [(v.exchange_id, checklist_brand(v.exchange_id, v.brand)) for v in venues]
        self.exchange.set_options(opts, selected=selected)

    def load(self, saved: dict[str, Any]) -> None:
        raw = saved.get("scan_exchanges")
        selected = [str(x) for x in raw] if isinstance(raw, list) else None
        self.refresh_exchange_options(selected=selected)
        self.vol.setValue(int(self._num(saved.get("min_volume_usd"), _DEFAULT_VOL)))
        self.every.setValue(int(self._num(saved.get("interval_minutes"), _DEFAULT_EVERY)))
        self._min_uniformity = self._num(saved.get("min_uniformity"), _DEFAULT_UNIT)
        self.heatmap.setChecked(bool(saved.get("heatmap_enabled", False)))
        self.refresh_compact_status()

    @staticmethod
    def _num(raw: object, default: float) -> float:
        if raw is None or raw == "":
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    def dump(self) -> dict[str, Any]:
        self.vol.interpretText()
        self.every.interpretText()
        return {
            "exchange": "All",
            "scan_exchanges": self.exchange.selected_ids(),
            "min_volume_usd": float(self.vol.value()),
            "min_uniformity": float(self._min_uniformity),
            "interval_minutes": int(self.every.value()),
            "heatmap_enabled": bool(self.heatmap.isChecked()),
        }

    def set_running(self, running: bool) -> None:
        self.run.setEnabled(not running)
        self.refresh_prices.setEnabled(not running)
        self.force_fresh.setEnabled(not running)
        self.sauce_pan.setEnabled(not running)
        self.pool_watch.setEnabled(not running)
        self.cancel.setEnabled(False)
        self.cancel.setVisible(not running)


class _EtaProxy:
    def __init__(self, bar: ScannerFilterBar) -> None:
        self._bar = bar

    def setText(self, text: str) -> None:  # noqa: N802 — Qt API
        self._bar.set_eta_text(text)

    def text(self) -> str:
        return self._bar._eta_part


def show_scan_status_dialog(status: str, parent: QWidget | None = None) -> None:
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

    dlg = QDialog(parent)
    dlg.setWindowTitle(S.SCANNER_STATUS)
    dlg.setModal(True)
    col = QVBoxLayout(dlg)
    body = QLabel(status or S.SCANNER_STATUS_EMPTY)
    body.setWordWrap(True)
    body.setObjectName("hint")
    body.setMinimumWidth(420)
    col.addWidget(body)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dlg.reject)
    close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
    if close_btn is not None:
        close_btn.clicked.connect(dlg.accept)
    col.addWidget(buttons)
    dlg.exec()
