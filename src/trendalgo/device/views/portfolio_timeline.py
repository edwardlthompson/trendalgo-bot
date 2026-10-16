"""Snapshot date picker for portfolio history (local portfolio.db)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from trendalgo.device import strings as S


class PortfolioTimeline(QFrame):
    def __init__(
        self,
        on_date: Callable[[str], None],
        parent: QFrame | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_date = on_date
        self._hint = QLabel(S.PORTFOLIO_ONE_SNAPSHOT)
        self._hint.setObjectName("hint")
        self._hint.setWordWrap(True)
        self._row = QFrame()
        row_layout = QHBoxLayout(self._row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel(S.PORTFOLIO_TIMELINE)
        self._label.setObjectName("hint")
        self._combo = QComboBox()
        self._combo.currentTextChanged.connect(self._picked)
        row_layout.addWidget(self._label)
        row_layout.addWidget(self._combo, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._hint)
        layout.addWidget(self._row)
        self.set_dates([])

    def set_dates(self, dates: list[str], *, selected: str | None = None) -> None:
        self._combo.blockSignals(True)
        self._combo.clear()
        for day in dates:
            self._combo.addItem(day)
        multi = len(dates) >= 2
        self._hint.setVisible(not multi)
        self._row.setVisible(multi)
        if multi:
            pick = selected if selected in dates else dates[0]
            self._combo.setCurrentIndex(dates.index(pick))
        self._combo.blockSignals(False)

    def _picked(self, day: str) -> None:
        if day:
            self._on_date(day)
