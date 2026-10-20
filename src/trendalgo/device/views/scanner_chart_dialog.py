"""Fullscreen scanner price chart with exclusive B&H-beater trade hold overlays."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from PySide6.QtCharts import QAreaSeries, QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
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

_CHART_MIN_WIDTH = 720


def show_scanner_chart_dialog(
    parent: QWidget,
    coin: dict[str, Any],
    *,
    window: str = "7d",
    candles_db: Path | None = None,
    price_only: bool = False,
    strategy_row: dict[str, Any] | None = None,
) -> None:
    """Price chart dialog.

    - ``price_only`` / B&H: no strategy radios, no trade overlays (Qualified spark default).
    - ``strategy_row``: single-strategy overlays (Results / Backtest Show Chart).
    - otherwise legacy multi-strategy radios from top_strategy_rows (kept for callers).
    """
    symbol = str(coin.get("symbol") or coin.get("pair") or "")
    closes = _closes_for_window(coin, window)
    name = str((strategy_row or {}).get("indicator") or "").strip()
    if name == "B&H":
        price_only = True
        strategy_row = None
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
    single = strategy_row is not None and not price_only
    show_trades.setChecked(bool(single) and not price_only)
    show_trades.setVisible(not price_only)
    radios_host = QWidget()
    radios_row = QHBoxLayout(radios_host)
    radios_row.setContentsMargins(0, 0, 0, 0)
    group = QButtonGroup(dialog)
    strategy_buttons: list[tuple[QRadioButton, dict[str, Any]]] = []
    if price_only:
        strategies: list[dict[str, Any]] = []
    elif single and strategy_row is not None:
        strategies = [strategy_row]
    else:
        strategies = top_strategy_rows(coin, limit=None)
    if price_only:
        pass
    elif not strategies:
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
    radios_scroll.setVisible(not price_only and not single)
    chart = _OverlayChart()
    chart.setMinimumWidth(_CHART_MIN_WIDTH)
    chart_scroll = QScrollArea()
    chart_scroll.setWidget(chart)
    chart_scroll.setWidgetResizable(True)
    chart_scroll.setFrameShape(QFrame.Shape.NoFrame)
    chart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    chart_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    if not price_only:
        layout.addWidget(show_trades)
    if not price_only and not single:
        layout.addWidget(radios_scroll)
    layout.addWidget(hint)
    layout.addWidget(chart_scroll, 1)
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
                        formula = ""
                        if str(row.get("indicator") or "").startswith("Secret Sauce"):
                            dossier = row.get("heartbeat_dossier")
                            if isinstance(dossier, dict):
                                formula = str(dossier.get("formula_en") or "")
                            if not formula and isinstance(row.get("params"), dict):
                                dossier = row["params"].get("heartbeat_dossier")
                                if isinstance(dossier, dict):
                                    formula = str(dossier.get("formula_en") or "")
                        base = f"{row.get('indicator')}: {n_trades} trades ({tsl_n} TSL exits)"
                        hint.setText(f"{base}\n{formula}" if formula else base)
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
    _open_windowed(dialog)
    dialog.exec()


def _open_windowed(dialog: QDialog) -> None:
    """Fill the available screen as a normal maximizable window (split-screen friendly)."""
    screen = dialog.screen() or QApplication.primaryScreen()
    if screen is not None:
        dialog.setGeometry(screen.availableGeometry())
    dialog.showMaximized()


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
        # Labels need mapped chart positions after axes/layout settle.
        pending = list(regions)

        def _place_labels() -> None:
            from shiboken6 import isValid

            if not isValid(self) or not isValid(self._chart):
                return
            for region in pending:
                if not isValid(self._chart):
                    return
                try:
                    self._add_region_label(region, colors)
                except RuntimeError:
                    return

        QTimer.singleShot(0, _place_labels)

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
        text = str(region.get("label") or "").strip()
        if not text:
            try:
                pct = float(region.get("pnl_pct"))  # type: ignore[arg-type]
                text = f"{pct:+.1f}%"
            except (TypeError, ValueError):
                return
        mid_ms = (start + end) / 2.0
        lo = min(float(region["entry_price"]), float(region["exit_price"]))
        hi = max(float(region["entry_price"]), float(region["exit_price"]))
        profitable = bool(region.get("profitable"))
        # Wins above the band; losses below — easier to read on dense overlays.
        anchor_px = hi if profitable else lo
        scene_pt = self._chart.mapToPosition(QPointF(mid_ms, anchor_px), self._price)
        item = QGraphicsSimpleTextItem(text)
        font = QFont(item.font())
        font.setBold(True)
        font.setPointSize(9)
        item.setFont(font)
        fill = colors["gainUp"] if profitable else colors["gainDown"]
        item.setBrush(QColor(fill))
        # Center label on the hold band mid-point.
        br = item.boundingRect()
        y_off = -br.height() - 2 if profitable else 4
        item.setPos(scene_pt.x() - br.width() / 2.0, scene_pt.y() + y_off)
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
