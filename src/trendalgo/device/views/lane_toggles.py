"""Settings: Auto-scan switches for Crypto / TradFi / Forex desks."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QCheckBox, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.lane_prefs import LanePrefs


class LaneToggles(QWidget):
    """Three Auto-scan switches (Settings Market lanes)."""

    def __init__(
        self,
        prefs: LanePrefs,
        *,
        on_changed: Callable[[LanePrefs], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_changed = on_changed
        self._crypto = QCheckBox(S.LANE_AUTO_SCAN_CRYPTO)
        self._tradfi = QCheckBox(S.LANE_AUTO_SCAN_TRADFI)
        self._forex = QCheckBox(S.LANE_AUTO_SCAN_FOREX)
        for box in (self._crypto, self._tradfi, self._forex):
            box.setToolTip(S.LANE_AUTO_SCAN_TIP)
        self.set_prefs(prefs)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        for box in (self._crypto, self._tradfi, self._forex):
            lay.addWidget(box)
            box.toggled.connect(lambda _c=False: self._emit())

    def prefs(self) -> LanePrefs:
        return LanePrefs(
            auto_scan_crypto=self._crypto.isChecked(),
            auto_scan_tradfi=self._tradfi.isChecked(),
            auto_scan_forex=self._forex.isChecked(),
        )

    def set_prefs(self, prefs: LanePrefs) -> None:
        for box, val in (
            (self._crypto, prefs.auto_scan_crypto),
            (self._tradfi, prefs.auto_scan_tradfi),
            (self._forex, prefs.auto_scan_forex),
        ):
            box.blockSignals(True)
            box.setChecked(val)
            box.blockSignals(False)

    def _emit(self) -> None:
        if self._on_changed is not None:
            self._on_changed(self.prefs())
