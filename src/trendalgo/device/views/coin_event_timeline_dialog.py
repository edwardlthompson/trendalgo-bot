"""Per-coin event timeline: 30d price + upcoming calendar markers (cache only)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCharts import (
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QScatterSeries,
    QValueAxis,
)
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.calendar.coin_window import load_coin_events, parse_event_day
from trendalgo.device.calendar.model import CalendarEvent
from trendalgo.device.calendar.quota import effective_ahead_days
from trendalgo.device.calendar.timeline_layout import day_to_ms, pack_callouts
from trendalgo.device.scanner_chart_trades import resolve_ohlcv_frame
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for


def open_coin_event_timeline(
    root: Path,
    coin: dict[str, Any],
    parent: QWidget | None = None,
    *,
    tier: str | None = "free",
) -> bool:
    """Open timeline when cache has events for this coin. Returns False if none."""
    events = load_coin_events(root, coin, tier=tier)
    if not events:
        return False
    dialog = _CoinEventTimelineDialog(root, coin, events, tier=tier or "free", parent=parent)
    dialog.exec()
    return True


class _CoinEventTimelineDialog(QDialog):
    def __init__(
        self,
        root: Path,
        coin: dict[str, Any],
        events: list[CalendarEvent],
        *,
        tier: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        symbol = str(coin.get("symbol") or coin.get("pair") or "")
        self.setWindowTitle(S.COIN_EVENTS_TITLE.format(symbol=symbol))
        self.setMinimumWidth(720)
        self.setMinimumHeight(520)
        layout = QVBoxLayout(self)
        hint = QLabel(S.COIN_EVENTS_HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        ahead = effective_ahead_days(tier)
        chart = _EventPriceChart()
        closes = _closes_30d(coin)
        frame = resolve_ohlcv_frame(
            coin, timeframe="1h", candles_db=None, for_overlay=False, closes=closes
        )
        markers = pack_callouts(
            [
                (
                    _event_day(e) or datetime.now(tz=UTC).date(),
                    e.title,
                    e.displayed_date or e.date[:10],
                    e.is_estimated,
                    e.url,
                )
                for e in events
                if _event_day(e) is not None
            ]
        )
        chart.set_data(frame, closes, markers, ahead_days=ahead)
        layout.addWidget(chart, stretch=2)
        list_host = QLabel(_format_list(markers))
        list_host.setWordWrap(True)
        list_host.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        list_host.setOpenExternalLinks(True)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(list_host)
        layout.addWidget(scroll, stretch=1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close is not None:
            close.clicked.connect(self.accept)
        layout.addWidget(buttons)
        _ = root


class _EventPriceChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._empty = QLabel(S.SCANNER_CHART_EMPTY)
        self._empty.setObjectName("hint")
        self._price = QLineSeries()
        self._chart = QChart()
        self._chart.addSeries(self._price)
        self._chart.legend().hide()
        self._chart.setBackgroundVisible(False)
        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("MMM d")
        self._axis_y = QValueAxis()
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)
        self._price.attachAxis(self._axis_x)
        self._price.attachAxis(self._axis_y)
        self._scatters: list[QScatterSeries] = []
        self._stems: list[QLineSeries] = []
        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._empty)
        lay.addWidget(self._view)
        self._empty.show()
        self._view.hide()

    def set_data(
        self,
        frame: Any,
        closes: list[float],
        markers: list[Any],
        *,
        ahead_days: int,
    ) -> None:
        self._clear_extras()
        self._price.clear()
        points = _price_points(frame, closes)
        if len(points) < 2:
            self._empty.show()
            self._view.hide()
            return
        colors = colors_for(active_mode())
        lows: list[float] = []
        highs: list[float] = []
        for ms, value in points:
            self._price.append(float(ms), float(value))
            lows.append(value)
            highs.append(value)
        self._price.setColor(QColor(colors["primary"]))
        first_ms, last_price_ms = points[0][0], points[-1][0]
        end_ms = max(
            last_price_ms,
            day_to_ms(datetime.now(tz=UTC).date() + timedelta(days=max(1, ahead_days))),
        )
        mid_y = (min(lows) + max(highs)) / 2.0
        for marker in markers:
            ms = float(day_to_ms(marker.day))
            stem = QLineSeries()
            stem.append(ms, min(lows))
            stem.append(ms, max(highs))
            pen = QColor(colors["outline"])
            pen.setAlpha(140)
            stem.setColor(pen)
            self._chart.addSeries(stem)
            stem.attachAxis(self._axis_x)
            stem.attachAxis(self._axis_y)
            self._stems.append(stem)
            scatter = QScatterSeries()
            scatter.setMarkerSize(14.0)
            scatter.setColor(QColor(colors["primary"]))
            scatter.append(ms, mid_y)
            tip = f"{marker.index}. {marker.displayed_date} — {marker.title}"
            if marker.is_estimated:
                tip = f"{tip} ({S.COIN_EVENTS_ESTIMATED})"
            scatter.setName(tip)
            self._chart.addSeries(scatter)
            scatter.attachAxis(self._axis_x)
            scatter.attachAxis(self._axis_y)
            self._scatters.append(scatter)
        self._axis_x.setRange(
            QDateTime.fromMSecsSinceEpoch(int(first_ms)),
            QDateTime.fromMSecsSinceEpoch(int(end_ms)),
        )
        low, high = min(lows), max(highs)
        pad = max((high - low) * 0.08, 1e-6)
        self._axis_y.setRange(low - pad, high + pad)
        self._empty.hide()
        self._view.show()

    def _clear_extras(self) -> None:
        for series in self._scatters + self._stems:
            self._chart.removeSeries(series)
        self._scatters.clear()
        self._stems.clear()


def _closes_30d(coin: dict[str, Any]) -> list[float]:
    raw = coin.get("spark_closes_30d") or coin.get("closes_1h") or coin.get("chart_closes_1h") or []
    out: list[float] = []
    for x in raw:
        if isinstance(x, int | float):
            out.append(float(x))
    return out


def _price_points(frame: Any, closes: list[float]) -> list[tuple[int, float]]:
    if frame is not None and getattr(frame, "empty", True) is False:
        try:
            from trendalgo.device.candle_chart_data import ohlc_bars

            bars = ohlc_bars(frame)
            if len(bars) >= 2:
                return [(b.ms, b.close) for b in bars]
        except Exception:
            pass
    if len(closes) < 2:
        return []
    now = datetime.now(tz=UTC)
    step = 3600 * 1000
    start = int(now.timestamp() * 1000) - (len(closes) - 1) * step
    return [(start + i * step, float(v)) for i, v in enumerate(closes)]


def _event_day(event: CalendarEvent) -> Any:
    return parse_event_day(event.date)


def _format_list(markers: list[Any]) -> str:
    if not markers:
        return S.COIN_EVENTS_NONE
    lines: list[str] = []
    for m in markers:
        est = f" · {S.COIN_EVENTS_ESTIMATED}" if m.is_estimated else ""
        title = m.title
        if m.url:
            title = f'<a href="{m.url}">{m.title}</a>'
        callout = " ★" if m.show_callout else ""
        lines.append(f"<b>{m.index}.</b> {m.displayed_date} — {title}{est}{callout}")
    return "<br/>".join(lines)
