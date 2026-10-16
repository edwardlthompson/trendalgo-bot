"""Stacked horizontal allocation bar for Portfolio Overview."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for

_SEGMENT_KEYS = (
    "primary",
    "secondary",
    "tertiary",
    "error",
    "primaryContainer",
    "secondaryContainer",
    "gainUp",
    "outline",
)


class PortfolioAllocationBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self._segments: list[tuple[str, float, str]] = []
        self._title = QLabel(S.PORTFOLIO_ALLOCATION)
        self._title.setObjectName("hint")
        self._bar = _BarPaint()
        self._legend = QLabel("")
        self._legend.setObjectName("hint")
        self._legend.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._title)
        layout.addWidget(self._bar)
        layout.addWidget(self._legend)

    def set_allocation(self, rows: list[dict[str, Any]]) -> None:
        colors = colors_for(active_mode())
        ranked = sorted(rows, key=lambda r: float(r.get("pct") or 0), reverse=True)
        segs: list[tuple[str, float, str]] = []
        other = 0.0
        for i, row in enumerate(ranked):
            pct = float(row.get("pct") or 0.0)
            if pct <= 0:
                continue
            if i < 8:
                key = _SEGMENT_KEYS[i % len(_SEGMENT_KEYS)]
                segs.append((str(row.get("asset") or "?"), pct, colors[key]))
            else:
                other += pct
        if other > 0:
            segs.append(("Other", other, colors["outline"]))
        self._segments = segs
        self._bar.set_segments(segs)
        self._legend.setText(
            " · ".join(f"{name} {pct * 100:.0f}%" for name, pct, _c in segs) or "—"
        )


class _BarPaint(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(22)
        self._segments: list[tuple[str, float, str]] = []

    def set_segments(self, segments: list[tuple[str, float, str]]) -> None:
        self._segments = segments
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = colors_for(active_mode())
        painter.fillRect(self.rect(), QColor(colors["surfaceVariant"]))
        if not self._segments:
            return
        x = 0.0
        width = float(self.width())
        height = float(self.height())
        for _name, pct, hex_color in self._segments:
            w = max(1.0, width * pct)
            painter.fillRect(int(x), 0, int(w), int(height), QColor(hex_color))
            x += w
