"""Simple holdings return heatmap (color grid) for the Portfolio page."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

from trendalgo.device import strings as S
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for


class HoldingsHeatmap(QFrame):
    def __init__(self, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self._title = QLabel(S.PORTFOLIO_HEATMAP)
        self._title.setObjectName("sectionTitle")
        self._empty = QLabel(S.PORTFOLIO_HEATMAP_EMPTY)
        self._empty.setObjectName("hint")
        self._empty.setWordWrap(True)
        self._grid_host = QFrame()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(6)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._title)
        layout.addWidget(self._empty)
        layout.addWidget(self._grid_host)
        self.set_rows([])

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        if not rows:
            self._empty.show()
            self._grid_host.hide()
            return
        self._empty.hide()
        self._grid_host.show()
        colors = colors_for(active_mode())
        cols = 5
        for index, row in enumerate(rows[:25]):
            cell = _Cell(str(row.get("asset", "")), float(row.get("return_pct", 0)), colors)
            self._grid.addWidget(cell, index // cols, index % cols)


class _Cell(QFrame):
    def __init__(self, asset: str, return_pct: float, colors: dict[str, str]) -> None:
        super().__init__()
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        ticker = QLabel(asset)
        ticker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ticker.setObjectName("sectionTitle")
        pct = QLabel(f"{return_pct:+.1f}%")
        pct.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pct.setObjectName("hint")
        layout.addWidget(ticker)
        layout.addWidget(pct)
        bg = QColor(colors["secondaryContainer"] if return_pct >= 0 else colors["error"])
        bg.setAlpha(72 if return_pct == 0 else 120)
        self.setStyleSheet(f"background: {bg.name(QColor.NameFormat.HexArgb)}; border-radius: 6px;")
