"""Top-level Alerts page with notify ribbon + Logs / Entered / Left / Trades tabs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.scanner_alerts_store import history_for_tab, load_history
from trendalgo.device.views.alerts_list import AlertsList
from trendalgo.device.views.alerts_notify_ribbon import AlertsNotifyRibbon
from trendalgo.device.views.widgets import TailFill

_TAB_KIND = {
    1: "entered",
    2: "left",
    3: "trades",
}


class AlertsPage(QWidget):
    def __init__(
        self,
        root: Path,
        *,
        on_toast: Callable[[str, str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = root
        self._ribbon = AlertsNotifyRibbon(root, on_toast=on_toast)
        self._tabs = QTabWidget()
        self._lists: dict[str, AlertsList] = {}
        for key, title in (
            ("logs", S.ALERTS_TAB_LOGS),
            ("entered", S.ALERTS_TAB_ENTERED),
            ("left", S.ALERTS_TAB_LEFT),
            ("trades", S.ALERTS_TAB_TRADES),
        ):
            panel = AlertsList()
            self._lists[key] = panel
            self._tabs.addTab(panel, title)
        self._tabs.currentChanged.connect(self._on_tab)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._ribbon)
        layout.addWidget(self._tabs, 1)
        self._fill = TailFill(layout, self._tabs)
        self.reload()

    def reload(self) -> None:
        rows = load_history(self._root)
        for key, panel in self._lists.items():
            panel.set_rows(history_for_tab(rows, key))
        self._ribbon.reload()
        self._fill.update(True)

    def _on_tab(self, index: int) -> None:
        kind = _TAB_KIND.get(index)
        if kind is not None:
            self._ribbon.set_kind(kind)
