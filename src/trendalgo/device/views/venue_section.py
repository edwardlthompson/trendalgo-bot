"""Settings: host vs device execution venue + one-time disclosure (Phase 3)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.execution_venue import (
    DISCLOSURE_TEXT,
    ExecutionVenueSettings,
    load_execution_venue,
    save_execution_venue,
)


class VenueSection(QWidget):
    def __init__(self, root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._root = root
        self._settings = load_execution_venue(root)
        self._venue = QComboBox()
        self._venue.addItem(S.SETTINGS_VENUE_HOST, "host")
        self._venue.addItem(S.SETTINGS_VENUE_DEVICE, "device")
        idx = 0 if self._settings.venue == "host" else 1
        self._venue.setCurrentIndex(idx)
        self._ack = QCheckBox(S.SETTINGS_VENUE_ACK)
        self._ack.setChecked(self._settings.disclosure_accepted)
        self._ack.setEnabled(not self._settings.disclosure_accepted)
        body = QLabel(DISCLOSURE_TEXT)
        body.setWordWrap(True)
        body.setObjectName("hint")
        save = QPushButton(S.SETTINGS_SAVE)
        save.clicked.connect(lambda _c=False: self._save())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(S.SETTINGS_VENUE))
        layout.addWidget(self._venue)
        layout.addWidget(body)
        layout.addWidget(self._ack)
        layout.addWidget(save)

    def _save(self) -> None:
        venue = str(self._venue.currentData())
        if venue not in ("host", "device"):
            venue = "host"
        if venue == "device" and not (self._ack.isChecked() or self._settings.disclosure_accepted):
            return
        accepted = self._settings.disclosure_accepted or self._ack.isChecked()
        updated = ExecutionVenueSettings(
            venue=venue,  # type: ignore[arg-type]
            disclosure_accepted=accepted
            if venue == "device"
            else self._settings.disclosure_accepted,
            first_bot_rails_lifted=self._settings.first_bot_rails_lifted,
        )
        if venue == "device" and not updated.disclosure_accepted:
            return
        save_execution_venue(self._root, updated)
        self._settings = updated
        if updated.disclosure_accepted:
            self._ack.setChecked(True)
            self._ack.setEnabled(False)
