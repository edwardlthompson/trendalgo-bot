"""Backtest candlestick chart with entry and exit markers (F-01 / O-02)."""

from __future__ import annotations

from typing import Any

import pandas as pd
from PySide6.QtCharts import (
    QCandlestickSeries,
    QCandlestickSet,
    QChart,
    QChartView,
    QDateTimeAxis,
    QScatterSeries,
    QValueAxis,
)
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.candle_chart_data import (
    TradeMarker,
    ohlc_bars,
    slice_frame_for_chart,
    trade_markers,
)
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for


class CandleChart(QWidget):
    """Candlesticks for one OHLCV window; scatter markers at trade entry and exit."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self._empty = QLabel(S.BACKTEST_CHART_EMPTY)
        self._empty.setObjectName("hint")
        self._empty.setWordWrap(True)
        self._candles = QCandlestickSeries()
        self._entries = QScatterSeries()
        self._entries.setName(S.BACKTEST_CHART_ENTRY)
        self._exits = QScatterSeries()
        self._exits.setName(S.BACKTEST_CHART_EXIT)
        self._chart = QChart()
        self._chart.addSeries(self._candles)
        self._chart.addSeries(self._entries)
        self._chart.addSeries(self._exits)
        self._chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        self._chart.setBackgroundVisible(False)
        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("MMM d hh:mm")
        self._axis_y = QValueAxis()
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)
        for series in (self._candles, self._entries, self._exits):
            series.attachAxis(self._axis_x)
            series.attachAxis(self._axis_y)
        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setMinimumHeight(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._empty)
        layout.addWidget(self._view)
        self.clear()

    def clear(self) -> None:
        self._candles.clear()
        self._entries.clear()
        self._exits.clear()
        self._empty.show()
        self._view.hide()

    def set_data(self, frame: pd.DataFrame, trades: list[dict[str, Any]]) -> None:
        self._candles.clear()
        self._entries.clear()
        self._exits.clear()
        window = slice_frame_for_chart(frame, trades)
        bars = ohlc_bars(window)
        entries, exits = trade_markers(trades)
        if len(bars) < 2:
            self.clear()
            return
        colors = colors_for(active_mode())
        self._entries.setColor(QColor(colors["secondary"]))
        self._exits.setColor(QColor(colors["error"]))
        self._entries.setMarkerSize(10.0)
        self._exits.setMarkerSize(10.0)
        self._entries.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeTriangle)
        self._exits.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeRotatedRectangle)
        for bar in bars:
            stick = QCandlestickSet(bar.open, bar.high, bar.low, bar.close, bar.ms)
            self._candles.append(stick)
        for marker in entries:
            self._append_marker(self._entries, marker)
        for marker in exits:
            self._append_marker(self._exits, marker)
        lows = [b.low for b in bars]
        highs = [b.high for b in bars]
        for marker in entries + exits:
            lows.append(marker.price)
            highs.append(marker.price)
        first, last = bars[0].ms, bars[-1].ms
        self._axis_x.setRange(
            QDateTime.fromMSecsSinceEpoch(first),
            QDateTime.fromMSecsSinceEpoch(last),
        )
        low, high = min(lows), max(highs)
        pad = max((high - low) * 0.06, 1e-6)
        self._axis_y.setRange(low - pad, high + pad)
        label = QColor(colors["onSurfaceVariant"])
        self._axis_x.setLabelsColor(label)
        self._axis_y.setLabelsColor(label)
        self._empty.hide()
        self._view.show()

    @staticmethod
    def _append_marker(series: QScatterSeries, marker: TradeMarker) -> None:
        series.append(marker.ms, marker.price)
