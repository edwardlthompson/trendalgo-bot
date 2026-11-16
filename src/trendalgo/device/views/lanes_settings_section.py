"""Settings: Market lanes (Auto-scan per desk) + Alpaca hint."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.lane_prefs import load_lane_prefs, save_lane_prefs
from trendalgo.device.views.alpaca_wizard import AlpacaWizardDialog
from trendalgo.device.views.lane_toggles import LaneToggles


class LanesSettingsSection(QWidget):
    def __init__(self, root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._root = root
        hint = QLabel(S.LANES_SETTINGS_HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        alpaca_hint = QLabel(S.LANES_ALPACA_HINT)
        alpaca_hint.setObjectName("hint")
        alpaca_hint.setWordWrap(True)
        alpaca_btn = QPushButton(S.NOTIFY_ALPACA_WIZARD)
        alpaca_btn.clicked.connect(lambda _c=False: AlpacaWizardDialog(parent=self).exec())
        self._lanes = LaneToggles(load_lane_prefs(root), on_changed=self._save)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(hint)
        layout.addWidget(alpaca_hint)
        layout.addWidget(alpaca_btn)
        layout.addWidget(self._lanes)

    def _save(self, prefs: object) -> None:
        from trendalgo.device.lane_prefs import LanePrefs

        if isinstance(prefs, LanePrefs):
            save_lane_prefs(self._root, prefs)

    def reload(self) -> None:
        self._lanes.set_prefs(load_lane_prefs(self._root))
