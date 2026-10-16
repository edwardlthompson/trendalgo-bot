"""Portfolio equity curve using QtCharts (O-02). One chart, not per-row sparklines."""

from __future__ import annotations

from typing import Any

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for


class EquityChart(QWidget):
    """Line chart of net worth over time. Shows a short note when history is too thin."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self._empty = QLabel(S.PORTFOLIO_NO_HISTORY)
        self._empty.setObjectName("hint")
        self._empty.setWordWrap(True)
        self._portfolio = QLineSeries()
        self._top10 = QLineSeries()
        self._buy_hold = QLineSeries()
        self._chart = QChart()
        for series in (self._portfolio, self._top10, self._buy_hold):
            self._chart.addSeries(series)
        self._chart.legend().setVisible(False)
        self._chart.setBackgroundVisible(False)
        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("MMM d")
        self._axis_y = QValueAxis()
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)
        for series in (self._portfolio, self._top10, self._buy_hold):
            series.attachAxis(self._axis_x)
            series.attachAxis(self._axis_y)
        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setMinimumHeight(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._empty)
        layout.addWidget(self._view)
        self.set_curves([])

    def set_points(self, points: list[dict[str, Any]]) -> None:
        """Backward-compatible single-series API."""
        self.set_curves(points)

    def set_curves(
        self,
        portfolio: list[dict[str, Any]],
        *,
        top10: list[dict[str, Any]] | None = None,
        buy_hold: list[dict[str, Any]] | None = None,
    ) -> None:
        self._portfolio.clear()
        self._top10.clear()
        self._buy_hold.clear()
        usable = [p for p in portfolio if _ms(p.get("captured_at")) is not None]
        if len(usable) < 2:
            self._empty.show()
            self._view.hide()
            self._chart.legend().hide()
            return
        self._empty.hide()
        self._view.show()
        colors = colors_for(active_mode())
        values = _fill_series(self._portfolio, usable, colors["primary"])
        if top10:
            _fill_series(self._top10, top10, colors["secondary"])
            self._top10.setName(S.PORTFOLIO_CHART_TOP10)
        if buy_hold:
            _fill_series(self._buy_hold, buy_hold, colors["onSurfaceVariant"])
            self._buy_hold.setName(S.PORTFOLIO_CHART_BUY_HOLD)
        self._portfolio.setName(S.PORTFOLIO_CHART_PORTFOLIO)
        self._chart.legend().setVisible(bool(top10 or buy_hold))
        first = _ms(usable[0]["captured_at"])
        last = _ms(usable[-1]["captured_at"])
        assert first is not None and last is not None
        self._axis_x.setRange(
            QDateTime.fromMSecsSinceEpoch(first), QDateTime.fromMSecsSinceEpoch(last)
        )
        low, high = min(values), max(values)
        for extra in (top10 or [], buy_hold or []):
            for point in extra:
                try:
                    low = min(low, float(point["total_usd"]))
                    high = max(high, float(point["total_usd"]))
                except (KeyError, TypeError, ValueError):
                    pass
        pad = max((high - low) * 0.08, 1.0)
        self._axis_y.setRange(low - pad, high + pad)
        self._axis_x.setLabelsColor(QColor(colors["onSurfaceVariant"]))
        self._axis_y.setLabelsColor(QColor(colors["onSurfaceVariant"]))


def _fill_series(series: QLineSeries, points: list[dict[str, Any]], color_hex: str) -> list[float]:
    series.setColor(QColor(color_hex))
    values: list[float] = []
    for point in points:
        ms = _ms(point.get("captured_at"))
        if ms is None:
            continue
        value = float(point["total_usd"])
        series.append(ms, value)
        values.append(value)
    return values


def _ms(raw: object) -> int | None:
    text = str(raw or "")
    if not text:
        return None
    # Daily aggregates use YYYY-MM-DD; snapshots use ISO datetimes.
    if len(text) == 10 and text[4] == "-":
        dt = QDateTime.fromString(text, "yyyy-MM-dd")
    else:
        dt = QDateTime.fromString(text, Qt.DateFormat.ISODate)
    if not dt.isValid():
        return None
    return int(dt.toMSecsSinceEpoch())
