"""Top-level Alerts page (scan enter/leave history)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout, QWidget

from trendalgo.device.scanner_alerts_store import load_history
from trendalgo.device.views.alerts_list import AlertsList
from trendalgo.device.views.widgets import TailFill


class AlertsPage(QWidget):
    def __init__(self, root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._root = root
        self._list = AlertsList()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list, 1)
        self._fill = TailFill(layout, self._list)
        self.reload()

    def reload(self) -> None:
        rows = load_history(self._root)
        self._list.set_rows(rows)
        self._fill.update(True)
