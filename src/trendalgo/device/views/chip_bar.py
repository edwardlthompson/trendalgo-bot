"""Reusable selectable chip row for Dashboard modules."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class ChipBar(QWidget):
    def __init__(
        self,
        chips: tuple[tuple[str, str], ...],
        *,
        exclusive: bool = True,
        on_change: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._exclusive = exclusive
        self._on_change = on_change
        self._buttons: dict[str, QPushButton] = {}
        self._selected: str | None = chips[0][0] if chips else None
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        for key, label in chips:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("chip")
            btn.setCursor(btn.cursor())
            btn.clicked.connect(lambda _c=False, k=key: self._click(k))
            self._buttons[key] = btn
            row.addWidget(btn)
        row.addStretch(1)
        self._sync()

    @property
    def selected(self) -> str | None:
        return self._selected

    def set_selected(self, key: str) -> None:
        if key in self._buttons:
            self._selected = key
            self._sync()

    def _click(self, key: str) -> None:
        if self._exclusive:
            self._selected = key
        self._sync()
        if self._on_change is not None:
            self._on_change(key)

    def _sync(self) -> None:
        for key, btn in self._buttons.items():
            btn.setChecked(key == self._selected)
