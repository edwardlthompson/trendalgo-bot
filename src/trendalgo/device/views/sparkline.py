"""In-cell sparkline: last-close amber ref, hi/lo, gainUp/gainDown price path."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from trendalgo.device import design_tokens as T
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for

SPARK_H = 48
SPARK_W = 192
# Cap paint points for dense 720-bar series; % below high still uses full window.
_MAX_PAINT = 240


def series_gain_pct(values: list[float]) -> float | None:
    """Percent change first→last when at least two finite closes exist."""
    clean = [v for v in values if v == v]
    if len(clean) < 2 or clean[0] == 0:
        return None
    return (clean[-1] - clean[0]) / abs(clean[0]) * 100.0


class Sparkline(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values: list[float] = []
        self._gain: float | None = None
        self._on_click: Callable[[], None] | None = None
        self.setMinimumSize(SPARK_W, SPARK_H)
        self.setMaximumHeight(SPARK_H + 4)

    def set_click_handler(self, handler: Callable[[], None] | None) -> None:
        self._on_click = handler
        if handler is None:
            self.unsetCursor()
        else:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event: object) -> None:  # noqa: ANN001
        button = getattr(event, "button", None)
        if (
            self._on_click is not None
            and callable(button)
            and button() == Qt.MouseButton.LeftButton
        ):
            self._on_click()
            return
        parent = getattr(super(), "mousePressEvent", None)
        if callable(parent):
            parent(event)

    def sizeHint(self) -> QSize:
        return QSize(SPARK_W, SPARK_H)

    def set_values(self, values: list[float], *, gain: float | None = None) -> None:
        self._values = [v for v in values if v == v]  # drop NaN
        self._gain = gain if gain is not None else series_gain_pct(self._values)
        self.update()

    def paintEvent(self, event: object) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = colors_for(active_mode())
        if len(self._values) < 2:
            painter.setPen(QColor(colors["onSurfaceVariant"]))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "—")
            return
        series = self._values
        if len(series) > _MAX_PAINT:
            step = max(1, len(series) // _MAX_PAINT)
            series = series[::step]
            if series[-1] != self._values[-1]:
                series = [*series, self._values[-1]]
        low, high = min(self._values), max(self._values)
        span = high - low or 1.0
        width = max(self.width() - 4, 1)
        height = max(self.height() - 4, 1)
        last = self._values[-1]

        def y_of(value: float) -> float:
            return 2 + height * (1.0 - (value - low) / span)

        if high > low:
            hilo = QPen(QColor(colors["onSurfaceVariant"]))
            hilo.setWidth(1)
            painter.setPen(hilo)
            painter.drawLine(2, int(y_of(low)), 2 + width, int(y_of(low)))
            painter.drawLine(2, int(y_of(high)), 2 + width, int(y_of(high)))
        ref = QPen(QColor(T.ACCENT_PRESETS[2]))
        ref.setWidth(1)
        painter.setPen(ref)
        painter.drawLine(2, int(y_of(last)), 2 + width, int(y_of(last)))
        points: list[QPointF] = []
        for index, value in enumerate(series):
            x = 2 + width * index / (len(series) - 1)
            points.append(QPointF(x, y_of(value)))
        if self._gain is None or self._gain >= 0:
            line = colors["gainUp"]
        else:
            line = colors["gainDown"]
        pen = QPen(QColor(line))
        pen.setWidth(2)
        painter.setPen(pen)
        for start, end in zip(points, points[1:], strict=False):
            painter.drawLine(start, end)
