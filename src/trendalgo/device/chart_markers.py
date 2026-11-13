"""Entry/exit triangle markers for Qt charts (Palette B)."""

from __future__ import annotations

from PySide6.QtCharts import QScatterSeries
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QPolygonF

from trendalgo.device import chart_contrast as C


def style_entry_series(series: QScatterSeries, *, size: float = 12.0) -> None:
    series.setMarkerSize(size)
    series.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeTriangle)
    series.setColor(QColor(C.ENTRY))
    series.setBorderColor(QColor(C.ENTRY_EDGE))


def style_exit_series(series: QScatterSeries, *, size: float = 12.0) -> None:
    """Down-triangle via pixmap (Qt has no inverted MarkerShapeTriangle)."""
    series.setMarkerSize(size)
    series.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeRectangle)
    pix = _down_triangle_pixmap(int(size) + 4)
    series.setBrush(pix)
    series.setPen(Qt.PenStyle.NoPen)
    series.setColor(QColor(C.EXIT))
    series.setBorderColor(QColor(C.EXIT_EDGE))


def _down_triangle_pixmap(side: int) -> QPixmap:
    pix = QPixmap(side, side)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(C.EXIT))
    painter.setPen(QColor(C.EXIT_EDGE))
    mid = side / 2.0
    poly = QPolygonF([QPointF(0, 1), QPointF(side - 1, 1), QPointF(mid, side - 1)])
    painter.drawPolygon(poly)
    painter.end()
    return pix
