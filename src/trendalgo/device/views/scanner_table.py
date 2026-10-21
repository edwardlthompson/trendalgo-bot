"""Dense LTS scanner table: Watch|Logo|Name, hourly sparks, optional heat ranks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from trendalgo.device import strings as S
from trendalgo.device.lts_scan_model import cell_gain, dash
from trendalgo.device.scan_identity import coin_in_watchlist, row_key
from trendalgo.device.scanner_heat import HEAT_COL_KEYS, INVERT_KEYS, fg_for_bg, rank_hex_colors
from trendalgo.device.scanner_sort import header_label
from trendalgo.device.views.scanner_table_cells import (
    COL_LOGO,
    COL_NAME,
    COL_WATCH,
    LOGO_PX,
    best_pill,
    exchange_chip,
    logo_cell,
    name_cell,
    results_btn,
    spark_cell,
    watch_cell,
)
from trendalgo.device.views.sparkline import SPARK_W
from trendalgo.device.views.widgets import tint_signed

# Watch, Logo, Name, 7D%, 7D, 30D%, 30D, Best BT, Bot vs B&H,
# Uniformity, Health, HV 7D, Max DD, Vol Δ%, Exchange, 24H Vol, Results
COLUMNS = 17
ROW_PX = 80
COL_SPARK7, COL_SPARK30 = 4, 6
COL_BEST, COL_EXCHANGE, COL_RESULTS = 7, 14, 16
COL_GAIN7, COL_GAIN30, COL_BOT_VS_BH = 3, 5, 8

__all__ = [
    "COL_BEST",
    "COL_EXCHANGE",
    "COL_LOGO",
    "COL_NAME",
    "COL_RESULTS",
    "COL_SPARK7",
    "COL_SPARK30",
    "COL_WATCH",
    "COLUMNS",
    "fill_lts_table",
]


def fill_lts_table(
    table: QTableWidget,
    coins: list[dict[str, Any]],
    *,
    watch: set[str] | None = None,
    sort_key: str = "",
    sort_dir: int = -1,
    heatmap: bool = False,
    filter_row: bool = False,
    on_results: Callable[[dict[str, Any]], None] | None = None,
    on_watch: Callable[[str, bool], None] | None = None,
    on_spark: Callable[[dict[str, Any], str], None] | None = None,
) -> None:
    from trendalgo.device.scanner_sort import COL_SORT_KEYS

    pinned = watch or set()
    heat_by_col = _heat_map(coins) if heatmap else {}
    offset = 1 if filter_row else 0
    if filter_row:
        # Keep row 0 filter widgets alive — clearContents() would destroy them mid-edit.
        while table.rowCount() > 1:
            table.removeRow(table.rowCount() - 1)
        table.setRowCount(len(coins) + offset)
    else:
        table.clearContents()
        table.setRowCount(len(coins) + offset)
    table.setColumnCount(COLUMNS)
    labels = [
        header_label(
            S.SCANNER_LTS_HEADERS[i],
            active=COL_SORT_KEYS.get(i) == sort_key,
            direction=sort_dir,
        )
        for i in range(COLUMNS)
    ]
    table.setHorizontalHeaderLabels(labels)
    _apply_header_tips(table)
    _apply_column_widths(table)
    table.verticalHeader().setDefaultSectionSize(ROW_PX)
    for row, coin in enumerate(coins):
        r = row + offset
        symbol = str(coin.get("symbol") or "")
        name = str(coin.get("name") or symbol)
        gain7 = cell_gain(coin, "7d")
        gain30 = cell_gain(coin, "30d")
        spark7 = list(coin.get("spark_closes_7d") or [])
        spark30 = list(coin.get("spark_closes_30d") or [])
        values = [
            "",
            "",
            "",
            dash(gain7, pct=True),
            "",
            dash(gain30, pct=True),
            "",
            "",
            dash(coin.get("bot_vs_bh_pct"), pct=True),
            dash(coin.get("uniformity_score")),
            dash(coin.get("health_score")),
            dash(coin.get("hv_7d_pct"), pct=True),
            dash(coin.get("max_drawdown_pct"), pct=True),
            dash(coin.get("volume_acceleration_pct"), pct=True),
            "",
            dash(coin.get("volume_24h"), money=True),
            "",
        ]
        skip = {
            COL_LOGO,
            COL_WATCH,
            COL_NAME,
            COL_SPARK7,
            COL_SPARK30,
            COL_BEST,
            COL_EXCHANGE,
            COL_RESULTS,
        }
        for column, text in enumerate(values):
            if column in skip:
                continue
            item = QTableWidgetItem(text)
            table.setItem(r, column, item)
            heat = heat_by_col.get(column, [None] * len(coins))[row] if heatmap else None
            if heat:
                item.setBackground(QColor(heat))
                item.setForeground(QColor(fg_for_bg(heat)))
            elif not heatmap:
                if column == COL_GAIN7 and gain7 is not None:
                    tint_signed(item, gain7)
                if column == COL_GAIN30 and gain30 is not None:
                    tint_signed(item, gain30)
                if column == COL_BOT_VS_BH:
                    try:
                        tint_signed(item, float(coin.get("bot_vs_bh_pct") or 0))
                    except (TypeError, ValueError):
                        pass
        watch_cell(table, r, row_key(coin), coin_in_watchlist(coin, pinned), on_watch)
        logo_cell(table, r, symbol, bool(coin.get("is_new")))
        name_cell(table, r, coin, symbol, name)
        spark7_click = _spark_handler(on_spark, coin, "7d")
        spark30_click = _spark_handler(on_spark, coin, "30d")
        spark_cell(
            table,
            r,
            COL_SPARK7,
            [float(x) for x in spark7 if isinstance(x, int | float)],
            coin.get("chart_dist_7d_pct"),
            gain7,
            on_click=spark7_click,
        )
        spark_cell(
            table,
            r,
            COL_SPARK30,
            [float(x) for x in spark30 if isinstance(x, int | float)],
            coin.get("chart_dist_30d_pct"),
            gain30,
            on_click=spark30_click,
        )
        best_heat = heat_by_col.get(COL_BEST, [None] * len(coins))[row] if heatmap else None
        best_pill(table, r, coin, heat_bg=best_heat)
        exchange_chip(table, r, coin)
        results_btn(table, r, coin, on_results)


def _spark_handler(
    on_spark: Callable[[dict[str, Any], str], None] | None,
    coin: dict[str, Any],
    window: str,
) -> Callable[[], None] | None:
    if on_spark is None:
        return None

    def _click() -> None:
        on_spark(coin, window)

    return _click


def _heat_map(coins: list[dict[str, Any]]) -> dict[int, list[str | None]]:
    from trendalgo.device.scanner_sort import field_value

    out: dict[int, list[str | None]] = {}
    for column, key in HEAT_COL_KEYS.items():
        values: list[float | None] = []
        for coin in coins:
            raw = field_value(coin, key)
            if raw is None or isinstance(raw, bool):
                values.append(None)
                continue
            if isinstance(raw, int | float):
                values.append(float(raw))
            elif isinstance(raw, str):
                try:
                    values.append(float(raw))
                except ValueError:
                    values.append(None)
            else:
                values.append(None)
        out[column] = rank_hex_colors(values, invert=key in INVERT_KEYS)
    return out


def _apply_header_tips(table: QTableWidget) -> None:
    tips = S.SCANNER_LTS_HEADER_TIPS
    for column, tip in enumerate(tips):
        item = table.horizontalHeaderItem(column)
        if item is None:
            item = QTableWidgetItem(S.SCANNER_LTS_HEADERS[column])
            table.setHorizontalHeaderItem(column, item)
        item.setToolTip(tip)


def _apply_column_widths(table: QTableWidget) -> None:
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(COL_LOGO, QHeaderView.ResizeMode.Fixed)
    header.setSectionResizeMode(COL_SPARK7, QHeaderView.ResizeMode.Fixed)
    header.setSectionResizeMode(COL_SPARK30, QHeaderView.ResizeMode.Fixed)
    table.setColumnWidth(COL_LOGO, LOGO_PX + 16)
    table.setColumnWidth(COL_SPARK7, SPARK_W + 48)
    table.setColumnWidth(COL_SPARK30, SPARK_W + 48)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
