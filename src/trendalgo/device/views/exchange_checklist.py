"""Compact checklist dropdown for multi-select exchanges."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QPushButton, QWidget

from trendalgo.device import strings as S


class ExchangeChecklist(QPushButton):
    """Button that opens a checkable menu; emits changed when selection changes."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("exchangeChecklist")
        self.setMinimumHeight(28)
        self._items: list[tuple[str, str]] = []  # (id, brand)
        self._checked: set[str] = set()
        self._menu = QMenu(self)
        self.setMenu(self._menu)
        self._refresh_label()

    def set_options(
        self,
        options: list[tuple[str, str]],
        *,
        selected: list[str] | None = None,
    ) -> None:
        """options = [(exchange_id, brand), ...]."""
        self._items = [(str(i).strip().lower(), str(b)) for i, b in options if str(i).strip()]
        ids = {i for i, _ in self._items}
        if selected is None:
            self._checked = set(ids)
        else:
            self._checked = {str(x).strip().lower() for x in selected if str(x).strip()} & ids
        self._rebuild_menu()
        self._refresh_label()

    def selected_ids(self) -> list[str]:
        order = [i for i, _ in self._items]
        return [i for i in order if i in self._checked]

    def filter_ids(self) -> list[str] | None:
        """None = no exchange filter (no keyed venues); else allow-list (may be empty)."""
        if not self._items:
            return None
        return self.selected_ids()

    def set_selected_ids(self, ids: list[str]) -> None:
        allowed = {i for i, _ in self._items}
        self._checked = {str(x).strip().lower() for x in ids if str(x).strip()} & allowed
        self._rebuild_menu()
        self._refresh_label()

    def _rebuild_menu(self) -> None:
        self._menu.clear()
        if not self._items:
            empty = QAction(S.SCANNER_EXCHANGES_NEED_KEYS, self._menu)
            empty.setEnabled(False)
            self._menu.addAction(empty)
            return
        group = QActionGroup(self._menu)
        group.setExclusive(False)
        for eid, brand in self._items:
            action = QAction(brand, self._menu)
            action.setCheckable(True)
            action.setChecked(eid in self._checked)
            action.setData(eid)
            action.toggled.connect(self._on_toggled)
            group.addAction(action)
            self._menu.addAction(action)

    def _on_toggled(self, checked: bool) -> None:
        action = self.sender()
        if not isinstance(action, QAction):
            return
        eid = str(action.data() or "")
        if not eid:
            return
        if checked:
            self._checked.add(eid)
        else:
            self._checked.discard(eid)
        self._refresh_label()
        self.changed.emit()

    def _refresh_label(self) -> None:
        brands = [b for i, b in self._items if i in self._checked]
        if not self._items:
            self.setText(S.SCANNER_EXCHANGES_NEED_KEYS)
            return
        if not brands:
            self.setText(S.SCANNER_EXCHANGES_NONE)
            return
        if len(brands) == len(self._items):
            self.setText(S.SCANNER_EXCHANGES_ALL)
            return
        if len(brands) <= 2:
            self.setText(", ".join(brands))
            return
        self.setText(S.SCANNER_EXCHANGES_N.format(n=len(brands)))


def wire_checklist(
    box: ExchangeChecklist,
    *,
    on_change: Callable[[], None],
) -> None:
    box.changed.connect(lambda: on_change())
