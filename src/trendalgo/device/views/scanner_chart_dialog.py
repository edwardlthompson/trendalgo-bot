"""Fullscreen scanner price chart with exclusive B&H-beater trade hold overlays."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from PySide6.QtCharts import QAreaSeries, QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, QPointF, Qt
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGraphicsSimpleTextItem,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.candle_chart_data import timestamp_ms
from trendalgo.device.scan_stake import DEVICE_SCAN_STAKE_USD
from trendalgo.device.scanner_chart_trades import (
    overlay_net_pct,
    regions_for_strategy,
    resolve_ohlcv_frame,
    top_strategy_rows,
)
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for


def show_scanner_chart_dialog(
    parent: QWidget,
    coin: dict[str, Any],
    *,
    window: str = "7d",
    candles_db: Path | None = None,
) -> None:
    symbol = str(coin.get("symbol") or coin.get("pair") or "")
    closes = _closes_for_window(coin, window)
    dialog = QDialog(parent)
    dialog.setWindowTitle(S.SCANNER_CHART_TITLE.format(symbol=symbol))
    dialog.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.WindowCloseButtonHint
        | Qt.WindowType.WindowMinMaxButtonsHint
    )
    layout = QVBoxLayout(dialog)
    hint = QLabel()
    hint.setObjectName("hint")
    hint.setWordWrap(True)
    show_trades = QCheckBox(S.SCANNER_CHART_SHOW_TRADES)
    show_trades.setChecked(True)
    radios_host = QWidget()
    radios_row = QHBoxLayout(radios_host)
    radios_row.setContentsMargins(0, 0, 0, 0)
    group = QButtonGroup(dialog)
    strategies = top_strategy_rows(coin, limit=None)
    strategy_buttons: list[tuple[QRadioButton, dict[str, Any]]] = []
    if not strategies:
        radios_row.addWidget(QLabel(S.SCANNER_CHART_NO_STRATEGIES))
    else:
        for index, row in enumerate(strategies):
            ind = str(row.get("indicator") or f"#{index + 1}")
            tf = str(row.get("timeframe") or "")
            label = f"{ind}@{tf}" if tf else ind
            btn = QRadioButton(label)
            group.addButton(btn, index)
            radios_row.addWidget(btn)
            strategy_buttons.append((btn, row))
            if index == 0:
                btn.setChecked(True)
    radios_row.addStretch(1)
    radios_scroll = QScrollArea()
    radios_scroll.setWidget(radios_host)
    radios_scroll.setWidgetResizable(True)
    radios_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    radios_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    radios_scroll.setFixedHeight(44)
    radios_scroll.setEnabled(True)
    chart = _OverlayChart()
    layout.addWidget(show_trades)
    layout.addWidget(radios_scroll)
    layout.addWidget(hint)
    layout.addWidget(chart, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    QShortcut(QKeySequence(Qt.Key.Key_Escape), dialog, dialog.reject)

    frame_cache: dict[str, pd.DataFrame] = {}
    region_cache: dict[int, list[dict[str, Any]]] = {}
    refreshing = False

    def _frame_for(row: dict[str, Any], *, for_overlay: bool) -> pd.DataFrame:
        tf = str(row.get("timeframe") or "1h")
        key = f"{tf}:{'bt' if for_overlay else 'ui'}"
        if key not in frame_cache:
            frame_cache[key] = resolve_ohlcv_frame(
                coin,
                timeframe=tf,
                candles_db=candles_db,
                closes=None if for_overlay else closes,
                for_overlay=for_overlay,
            )
        return frame_cache[key]

    def _refresh(_checked: bool = False) -> None:
        nonlocal refreshing
        if refreshing:
            return
        refreshing = True
        try:
            if not closes and not strategies:
                chart.clear()
                hint.setText(S.SCANNER_CHART_EMPTY)
                return
            regions: list[dict[str, Any]] = []
            display = resolve_ohlcv_frame(
                coin, timeframe="1h", candles_db=candles_db, closes=closes, for_overlay=False
            )
            if show_trades.isChecked() and strategy_buttons:
                radios_scroll.setEnabled(True)
                checked_id = group.checkedId()
                if checked_id < 0:
                    checked_id = 0
                    strategy_buttons[0][0].blockSignals(True)
                    strategy_buttons[0][0].setChecked(True)
                    strategy_buttons[0][0].blockSignals(False)
                row = strategy_buttons[checked_id][1]
                display = _frame_for(row, for_overlay=True)
                if checked_id not in region_cache:
                    try:
                        region_cache[checked_id] = regions_for_strategy(
                            display,
                            row,
                            stake_usd=DEVICE_SCAN_STAKE_USD,
                        )
                    except Exception as exc:  # noqa: BLE001 — keep UI alive on TA failures
                        region_cache[checked_id] = []
                        hint.setText(f"Overlay failed for {row.get('indicator')}: {exc}")
                        chart.set_frame(display if not display.empty else None, closes, [])
                        return
                regions = region_cache[checked_id]
                n_trades = len(regions)
                tsl_n = sum(1 for r in regions if r.get("tsl_exit"))
                expected = row.get("trades")
                if not regions:
                    hint.setText("No trades for this strategy on the available bars.")
                elif expected is not None and int(expected) != n_trades:
                    hint.setText(
                        f"{row.get('indicator')}: overlay {n_trades} trades "
                        f"(Results listed {expected}; {tsl_n} TSL)."
                    )
                else:
                    overlay_net = overlay_net_pct(regions)
                    results_net = _as_float(row.get("net_pct"))
                    if (
                        overlay_net is not None
                        and results_net is not None
                        and abs(overlay_net - results_net) > 1.0
                    ):
                        hint.setText(
                            S.SCANNER_CHART_NET_MISMATCH.format(
                                indicator=row.get("indicator"),
                                overlay=overlay_net,
                                results=results_net,
                                trades=n_trades,
                                tsl_n=tsl_n,
                            )
                        )
                    else:
                        hint.setText(
                            f"{row.get('indicator')}: {n_trades} trades ({tsl_n} TSL exits)"
                        )
            else:
                radios_scroll.setEnabled(False)
                hint.clear()
            if display.empty and not closes:
                chart.clear()
                hint.setText(S.SCANNER_CHART_EMPTY)
                return
            chart.set_frame(display if not display.empty else None, closes, regions)
        finally:
            refreshing = False

    show_trades.toggled.connect(_refresh)
    group.idToggled.connect(lambda _id, on: _refresh() if on else None)
    _refresh()
    _open_fullscreen(dialog)
    dialog.exec()


def _open_fullscreen(dialog: QDialog) -> None:
    screen = dialog.screen() or QApplication.primaryScreen()
    if screen is not None:
        dialog.setGeometry(screen.geometry())
    dialog.showFullScreen()


def _closes_for_window(coin: dict[str, Any], window: str) -> list[float]:
    key = "spark_closes_30d" if window == "30d" else "spark_closes_7d"
    raw = coin.get(key) or coin.get("closes_1h") or coin.get("chart_closes_1h") or []
    if not isinstance(raw, list):
        return []
    return [float(x) for x in raw if isinstance(x, (int, float))]


def _as_float(raw: object) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _price_points(
    frame: pd.DataFrame | None,
    closes: list[float],
) -> list[tuple[int, float]]:
    if frame is not None and not frame.empty and "close" in frame.columns:
        out: list[tuple[int, float]] = []
        closes_col = frame["close"].astype(float).tolist()
        for stamp, value in zip(frame.index, closes_col, strict=True):
            ms = timestamp_ms(stamp)
            if ms is None:
                continue
            out.append((ms, float(value)))
        if len(out) >= 2:
            return out
    if len(closes) < 2:
        return []
    end = QDateTime.currentDateTimeUtc()
    step_ms = 3600_000
    return [
        (end.toMSecsSinceEpoch() - step_ms * (len(closes) - 1 - i), float(value))
        for i, value in enumerate(closes)
    ]


class _OverlayChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._empty = QLabel(S.SCANNER_CHART_EMPTY)
        self._empty.setObjectName("hint")
        self._price = QLineSeries()
        self._chart = QChart()
        self._chart.addSeries(self._price)
        self._chart.legend().hide()
        self._chart.setBackgroundVisible(False)
        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("MMM d hh:mm")
        self._axis_y = QValueAxis()
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)
        self._price.attachAxis(self._axis_x)
        self._price.attachAxis(self._axis_y)
        self._areas: list[QAreaSeries] = []
        self._area_lines: list[QLineSeries] = []
        self._labels: list[QGraphicsSimpleTextItem] = []
        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._empty)
        layout.addWidget(self._view)
        self.clear()

    def clear(self) -> None:
        self._clear_areas()
        self._price.clear()
        self._empty.show()
        self._view.hide()

    def set_frame(
        self,
        frame: pd.DataFrame | None,
        closes: list[float],
        regions: list[dict[str, Any]],
    ) -> None:
        self._clear_areas()
        self._price.clear()
        points = _price_points(frame, closes)
        if len(points) < 2:
            self.clear()
            return
        colors = colors_for(active_mode())
        for ms, value in points:
            self._price.append(ms, value)
        lows = [p[1] for p in points]
        highs = list(lows)
        for region in regions:
            area = self._add_region(region, colors)
            if area is not None:
                self._areas.append(area)
                lows.append(float(region["entry_price"]))
                lows.append(float(region["exit_price"]))
                highs.append(float(region["entry_price"]))
                highs.append(float(region["exit_price"]))
        self._price.setColor(QColor(colors["primary"]))
        first, last = points[0][0], points[-1][0]
        self._axis_x.setRange(
            QDateTime.fromMSecsSinceEpoch(first), QDateTime.fromMSecsSinceEpoch(last)
        )
        low, high = min(lows), max(highs)
        pad = max((high - low) * 0.06, 1e-6)
        self._axis_y.setRange(low - pad, high + pad)
        label = QColor(colors["onSurfaceVariant"])
        self._axis_x.setLabelsColor(label)
        self._axis_y.setLabelsColor(label)
        self._empty.hide()
        self._view.show()
        # Labels need mapped chart positions after axes are set.
        for region in regions:
            self._add_region_label(region, colors)

    def _add_region(self, region: dict[str, Any], colors: dict[str, str]) -> QAreaSeries | None:
        start = timestamp_ms(region.get("entry_time"))
        end = timestamp_ms(region.get("exit_time"))
        if start is None or end is None or end <= start:
            return None
        lo = min(float(region["entry_price"]), float(region["exit_price"]))
        hi = max(float(region["entry_price"]), float(region["exit_price"]))
        if hi <= lo:
            hi = lo * 1.001
        upper = QLineSeries()
        lower = QLineSeries()
        upper.append(float(start), hi)
        upper.append(float(end), hi)
        lower.append(float(start), lo)
        lower.append(float(end), lo)
        area = QAreaSeries(upper, lower)
        fill = colors["gainUp"] if region.get("profitable") else colors["gainDown"]
        color = QColor(fill)
        color.setAlpha(110)
        area.setColor(color)
        area.setBorderColor(QColor(fill))
        self._area_lines.extend((upper, lower))
        self._chart.addSeries(area)
        area.attachAxis(self._axis_x)
        area.attachAxis(self._axis_y)
        return area

    def _add_region_label(self, region: dict[str, Any], colors: dict[str, str]) -> None:
        start = timestamp_ms(region.get("entry_time"))
        end = timestamp_ms(region.get("exit_time"))
        if start is None or end is None:
            return
        text = str(region.get("label") or "")
        if not text:
            return
        mid_ms = (start + end) / 2.0
        mid_px = (float(region["entry_price"]) + float(region["exit_price"])) / 2.0
        scene_pt = self._chart.mapToPosition(QPointF(mid_ms, mid_px), self._price)
        item = QGraphicsSimpleTextItem(text)
        font = QFont(item.font())
        font.setBold(True)
        font.setPointSize(9)
        item.setFont(font)
        fill = colors["gainUp"] if region.get("profitable") else colors["gainDown"]
        item.setBrush(QColor(fill))
        # Slight offset so text sits above the band center.
        item.setPos(scene_pt.x() - 18, scene_pt.y() - 14)
        scene = self._chart.scene()
        if scene is not None:
            scene.addItem(item)
            self._labels.append(item)

    def _clear_areas(self) -> None:
        scene = self._chart.scene()
        for item in self._labels:
            if scene is not None:
                scene.removeItem(item)
        self._labels.clear()
        for area in self._areas:
            try:
                area.detachAxis(self._axis_x)
                area.detachAxis(self._axis_y)
            except RuntimeError:
                pass
            self._chart.removeSeries(area)
        self._areas.clear()
        self._area_lines.clear()
