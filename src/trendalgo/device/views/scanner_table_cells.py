"""Cell builders for the dense LTS scanner table (Watch|Cmp|Logo|Name …)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.coin_icons import coin_icon_path
from trendalgo.device.coin_listing import coin_listing_url
from trendalgo.device.lts_scan_model import dash, has_backtest_results
from trendalgo.device.scanner_heat import fg_for_bg
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.sparkline import Sparkline, series_gain_pct

LOGO_PX = 36
COL_WATCH, COL_CMP, COL_LOGO, COL_NAME = 0, 1, 2, 3
COL_BEST, COL_EXCHANGE, COL_RESULTS = 8, 15, 17


def logo_cell(table: QTableWidget, row: int, symbol: str, is_new: bool) -> None:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(2, 2, 2, 2)
    layout.setSpacing(0)
    layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    label = QLabel()
    label.setFixedSize(LOGO_PX, LOGO_PX)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    path = coin_icon_path(symbol)
    painted = False
    if path is not None:
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            label.setPixmap(
                pixmap.scaled(
                    LOGO_PX,
                    LOGO_PX,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            painted = True
    if not painted:
        label.setText(symbol[:3] or "?")
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter)
    if is_new:
        badge = QLabel(S.SCANNER_NEW_BADGE)
        badge.setObjectName("badgeNew")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)
    table.setCellWidget(row, COL_LOGO, host)


def watch_cell(
    table: QTableWidget,
    row: int,
    pair: str,
    is_pinned: bool,
    on_watch: Callable[[str, bool], None] | None,
) -> None:
    _check_cell(table, row, COL_WATCH, pair, is_pinned, on_watch, tip=S.SCANNER_TAB_WATCH)


def cmp_cell(
    table: QTableWidget,
    row: int,
    pair: str,
    checked: bool,
    on_compare: Callable[[str, bool], None] | None,
) -> None:
    _check_cell(table, row, COL_CMP, pair, checked, on_compare, tip=S.SCANNER_COMPARE_BTN)


def _check_cell(
    table: QTableWidget,
    row: int,
    column: int,
    pair: str,
    checked: bool,
    on_toggle: Callable[[str, bool], None] | None,
    *,
    tip: str,
) -> None:
    colors = colors_for(active_mode())
    box = QCheckBox()
    box.setToolTip(tip)
    box.setStyleSheet(
        f"QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid {colors['outline']};"
        f" border-radius: 3px; background: {colors['surface']}; }}"
        f"QCheckBox::indicator:checked {{ background: {colors['primary']};"
        f" border-color: {colors['primary']}; }}"
        f"QCheckBox::indicator:unchecked {{ background: {colors['background']}; }}"
    )
    box.blockSignals(True)
    box.setChecked(checked)
    box.blockSignals(False)
    if on_toggle is not None and pair:
        box.toggled.connect(lambda is_on, p=pair: on_toggle(p, bool(is_on)))
    wrap = QWidget()
    row_layout = QHBoxLayout(wrap)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.addStretch(1)
    row_layout.addWidget(box)
    row_layout.addStretch(1)
    table.setCellWidget(row, column, wrap)


def name_cell(
    table: QTableWidget,
    row: int,
    coin: dict[str, Any],
    symbol: str,
    name: str,
) -> None:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(0)
    url = coin_listing_url(coin)
    display = name if name else symbol
    if url:
        link = QLabel(f'<a href="{url}">{display}</a>')
        link.setTextFormat(Qt.TextFormat.RichText)
        link.setOpenExternalLinks(False)
        link.linkActivated.connect(lambda href: QDesktopServices.openUrl(QUrl(href)))
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    else:
        link = QLabel(display)
    layout.addWidget(link)
    if symbol and symbol != display:
        ticker = QLabel(symbol)
        ticker.setObjectName("hint")
        layout.addWidget(ticker)
    table.setCellWidget(row, COL_NAME, host)


def spark_cell(
    table: QTableWidget,
    row: int,
    column: int,
    closes: list[float],
    dist_pct: object,
    gain: float | None,
    *,
    on_click: Callable[[], None] | None = None,
) -> None:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(2, 0, 2, 0)
    layout.setSpacing(4)
    resolved = gain if gain is not None else series_gain_pct(closes)
    widget = Sparkline(host)
    widget.set_values(closes, gain=resolved)
    if on_click is not None:
        widget.set_click_handler(on_click)
    layout.addWidget(widget, stretch=1)
    if isinstance(dist_pct, int | float) and not isinstance(dist_pct, bool):
        pct_text = f"{float(dist_pct):.1f}%"
    elif isinstance(dist_pct, str):
        try:
            pct_text = f"{float(dist_pct):.1f}%"
        except ValueError:
            pct_text = "—"
    else:
        pct_text = "—"
    label = QLabel(pct_text)
    label.setObjectName("hint")
    label.setMinimumWidth(36)
    layout.addWidget(label)
    table.setCellWidget(row, column, host)


def best_pill(
    table: QTableWidget,
    row: int,
    coin: dict[str, Any],
    *,
    heat_bg: str | None = None,
) -> None:
    raw = coin.get("bot_best_net_pct")
    if raw is None:
        table.setItem(row, COL_BEST, QTableWidgetItem("—"))
        return
    try:
        value = float(raw)
    except (TypeError, ValueError):
        table.setItem(row, COL_BEST, QTableWidgetItem("—"))
        return
    frame = QFrame()
    frame.setObjectName("btBestPill")
    if heat_bg:
        bg = heat_bg
        fg = fg_for_bg(heat_bg)
    else:
        colors = colors_for(active_mode())
        bg = colors["surfaceVariant"]
        fg = colors["onSurface"]
    frame.setStyleSheet(
        f"QFrame#btBestPill {{ background: {bg}; border-radius: 6px; padding: 2px 6px; }}"
    )
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(0)
    top = QLabel(dash(value, pct=True))
    top.setAlignment(Qt.AlignmentFlag.AlignCenter)
    top.setStyleSheet(f"color: {fg}; font-weight: 600;")
    layout.addWidget(top)
    label = str(coin.get("bot_best_label") or "").strip()
    if label:
        sub = QLabel(label)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {fg}; font-size: 10px;")
        layout.addWidget(sub)
    table.setCellWidget(row, COL_BEST, frame)


def exchange_chip(table: QTableWidget, row: int, coin: dict[str, Any]) -> None:
    listed = [str(x) for x in (coin.get("listed_on") or ["kraken"])]
    text = ", ".join(x.title() for x in listed) or "Kraken"
    chip = QLabel(text)
    chip.setObjectName("exchangeChip")
    chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
    table.setCellWidget(row, COL_EXCHANGE, chip)


def results_btn(
    table: QTableWidget,
    row: int,
    coin: dict[str, Any],
    on_results: Callable[[dict[str, Any]], None] | None,
) -> None:
    btn = QPushButton(S.SCANNER_RESULTS)
    enabled = has_backtest_results(coin)
    btn.setEnabled(enabled)
    if enabled and on_results is not None:
        btn.clicked.connect(lambda _c=False, c=coin: on_results(c))
    table.setCellWidget(row, COL_RESULTS, btn)
