"""Results dialog: strategy sheet, glossary popups, one-click Create Bot, share export."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QLabel,
    QMessageBox,
    QScrollArea,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.backtest_results_ui import filter_perfect_rows
from trendalgo.device.backtest_row_filter import filter_rows
from trendalgo.device.icons import nav_icon
from trendalgo.device.results_view_prefs import load_results_prefs, save_results_prefs
from trendalgo.device.scanner_share import default_scanner_export_path, export_strategy_sheet_png
from trendalgo.device.scanner_signal_sets import BT_SET_ALL_TA, is_three_commas_indicator
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.backtest_column_filter_row import BacktestColumnFilterRow
from trendalgo.device.views.glossary_popup import show_glossary_popup
from trendalgo.device.views.scanner_results_fill import data_row_index, populate_results_table

_COLUMNS = S.BACKTEST_RESULT_HEADERS
_BH = "B&H"
_FILTER_DEBOUNCE_MS = 2000
CreateBotCb = Callable[[dict[str, str], str], str]


def strategy_sheet_rows(
    coin: dict[str, Any], *, top_n: int = 5, perfect_only: bool = False
) -> list[dict[str, Any]]:
    """Strategy rows for Results.

    All TA: full sheet (same keep rules as Backtest) plus B&H, sorted by net desc.
    3Commas / other: top_n by net plus B&H.
    """
    raw = coin.get("backtest_top_strategies")
    strategies = [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []
    bh = coin.get("backtest_buy_hold")
    oracle = coin.get("backtest_oracle_max")
    all_ta = str(coin.get("bt_signal_set") or "") == BT_SET_ALL_TA
    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in strategies:
        name = str(row.get("indicator") or "").strip()
        if name in {_BH, "Oracle max"}:
            continue
        net = _net(row)
        if net is None:
            continue
        ranked.append((net, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if all_ta:
        out = [dict(row) for _, row in ranked]
    else:
        out = [dict(row) for _, row in ranked[:top_n]]
    if isinstance(bh, dict):
        has_bh = any(str(r.get("indicator") or "").strip() == _BH for r in out)
        if not has_bh:
            row = dict(bh)
            row.setdefault("indicator", _BH)
            out.append(row)
    if isinstance(oracle, dict):
        has_or = any(str(r.get("indicator") or "").strip() == "Oracle max" for r in out)
        if not has_or:
            row = dict(oracle)
            row.setdefault("indicator", "Oracle max")
            out.append(row)
    out.sort(key=lambda row: (_net(row) is not None, _net(row) or 0.0), reverse=True)
    if perfect_only:
        out = filter_perfect_rows(out)
    return out


def indicator_display_label(
    indicator: str,
    *,
    bt_signal_set: str | None,
    is_bh: bool = False,
) -> str:
    """Asterisk 3Commas catalog ids only when the scan used All TA."""
    text = str(indicator or "—")
    if is_bh:
        return f"{_BH}  ← buy & hold" if text == _BH else text
    if text == "Oracle max":
        return S.BACKTEST_ORACLE_LABEL
    from trendalgo.device.sauce_names import is_sauce_lab, is_sauce_ta

    if is_sauce_ta(text):
        return S.SECRET_SAUCE_TA_LABEL
    if is_sauce_lab(text):
        return S.SECRET_SAUCE_LABEL
    if bt_signal_set == BT_SET_ALL_TA and is_three_commas_indicator(text):
        return f"{text} *"
    return text


def show_results_dialog(
    parent: QWidget,
    coin: dict[str, Any],
    *,
    heatmap: bool = False,
    perfect_only: bool = False,
    on_create_bot: CreateBotCb | None = None,
    export_root: Path | None = None,
    initial_filters: dict[str, Any] | None = None,
) -> None:
    symbol = str(coin.get("symbol") or coin.get("pair") or "")
    pair = str(coin.get("pair") or symbol)
    dialog = QDialog(parent)
    dialog.setWindowTitle(S.SCANNER_RESULTS_TITLE.format(symbol=symbol))
    dialog.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.WindowCloseButtonHint
        | Qt.WindowType.WindowMinMaxButtonsHint
    )
    dialog.setMinimumSize(520, 360)
    prefs_root = export_root
    layout = QVBoxLayout(dialog)
    status = QLabel()
    status.setObjectName("hint")
    status.setWordWrap(True)
    all_rows = strategy_sheet_rows(coin, perfect_only=perfect_only)
    # Same list object so cellClicked / share always see the latest filtered rows.
    visible: list[dict[str, Any]] = list(all_rows)
    body = QWidget()
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(0, 0, 0, 0)
    table: QTableWidget | None = None
    filters: BacktestColumnFilterRow | None = None
    if not all_rows:
        body_layout.addWidget(QLabel(S.SCANNER_RESULTS_EMPTY))
    else:
        table = QTableWidget(0, len(_COLUMNS))
        table.setHorizontalHeaderLabels(list(_COLUMNS))
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        filters = BacktestColumnFilterRow()
        filters.attach(table)
        if initial_filters:
            _apply_initial_filters(filters, initial_filters)
            visible[:] = filter_rows(all_rows, filters.dump())
        populate_results_table(
            table,
            visible,
            coin=coin,
            pair=pair,
            heatmap=heatmap,
            status=status,
            parent=dialog,
            filter_row=filters,
            on_create_bot=on_create_bot,
            indicator_label=indicator_display_label,
        )
        filter_timer = QTimer(dialog)
        filter_timer.setSingleShot(True)
        filter_timer.setInterval(_FILTER_DEBOUNCE_MS)

        def _refill() -> None:
            if table is None or filters is None:
                return
            visible[:] = filter_rows(all_rows, filters.dump())
            populate_results_table(
                table,
                visible,
                coin=coin,
                pair=pair,
                heatmap=heatmap,
                status=status,
                parent=dialog,
                filter_row=filters,
                on_create_bot=on_create_bot,
                indicator_label=indicator_display_label,
            )

        def _on_filter_changed(_text: str = "") -> None:
            filter_timer.start()

        filter_timer.timeout.connect(_refill)
        from PySide6.QtWidgets import QLineEdit

        for control in filters._by_col.values():  # noqa: SLF001 — same as BacktestPage
            if isinstance(control, QLineEdit):
                control.textChanged.connect(_on_filter_changed)
        table.cellClicked.connect(
            lambda row_i, col: _on_indicator_click(
                table,
                row_i,
                col,
                dialog,
                rows=visible,
                coin=coin,
                on_create_bot=on_create_bot,
                has_filter_row=True,
            )
        )
        body_layout.addWidget(table)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidget(body)
    layout.addWidget(scroll, 1)
    layout.addWidget(status)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    share = QToolButton()
    share.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    share.setIcon(nav_icon("share", colors_for(active_mode())["onSurfaceVariant"], 20))
    share.setToolTip(S.SCANNER_RESULTS_SHARE_TIP)
    share.setAccessibleName(S.SCANNER_SHARE)
    share.setEnabled(bool(all_rows) and export_root is not None)

    def _share(_checked: bool = False) -> None:
        export_rows = visible if visible else all_rows
        if export_root is None or not export_rows:
            return
        suggested = str(default_scanner_export_path(export_root, label=symbol or "pair"))
        chosen, _flt = QFileDialog.getSaveFileName(
            dialog, S.SCANNER_SHARE_DIALOG, suggested, S.SCANNER_SHARE_FILTER
        )
        if not chosen:
            return
        out = Path(chosen) if chosen.lower().endswith(".png") else Path(f"{chosen}.png")
        try:
            export_strategy_sheet_png(out, pair=pair or symbol, rows=export_rows, heatmap=heatmap)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(dialog, S.SCANNER_SHARE, str(exc))
            return
        QMessageBox.information(
            dialog,
            S.SCANNER_SHARE,
            S.SCANNER_SHARE_DONE.format(name=out.name, path=str(out.parent)),
        )

    share.clicked.connect(_share)
    buttons.addButton(share, QDialogButtonBox.ButtonRole.ActionRole)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    def _persist_geometry(_result: int = 0) -> None:
        if prefs_root is None:
            return
        prefs = load_results_prefs(prefs_root)
        maximized = bool(dialog.isMaximized())
        prefs.results_dialog_maximized = maximized
        if not maximized:
            prefs.results_dialog_width = max(520, dialog.width())
            prefs.results_dialog_height = max(360, dialog.height())
        save_results_prefs(prefs_root, prefs)

    dialog.finished.connect(_persist_geometry)
    if prefs_root is not None:
        prefs = load_results_prefs(prefs_root)
        dialog.resize(prefs.results_dialog_width, prefs.results_dialog_height)
        if prefs.results_dialog_maximized:
            dialog.showMaximized()
    dialog.exec()


def _apply_initial_filters(filters: BacktestColumnFilterRow, raw: dict[str, Any]) -> None:
    if raw.get("indicator_contains"):
        filters.indicator.setText(str(raw["indicator_contains"]))
    if raw.get("timeframe"):
        filters.timeframe.setText(str(raw["timeframe"]))
    if raw.get("params_contains"):
        filters.params.setText(str(raw["params_contains"]))
    _set_num(filters.min_net, raw.get("min_net_pct"))
    _set_num(filters.max_fees, raw.get("max_fees"))
    _set_num(filters.max_open, raw.get("max_open"), allow_zero=True)
    _set_num(filters.min_wins, raw.get("min_wins"))
    _set_num(filters.max_losses, raw.get("max_losses"), allow_zero=True)
    _set_num(filters.min_win, raw.get("min_win_pct"))
    _set_num(filters.max_tsl, raw.get("max_tsl_pct"))
    _set_num(filters.max_hits, raw.get("max_tsl_hits"), allow_zero=True)
    _set_num(filters.max_hit_pct, raw.get("max_tsl_hit_pct"))
    _set_num(filters.min_strength, raw.get("min_strength"))


def _set_num(edit: Any, value: object, *, allow_zero: bool = False) -> None:
    if value is None or value == "":
        return
    try:
        number = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return
    if number > 0 or (allow_zero and number == 0):
        edit.setText(str(number))


def _on_indicator_click(
    table: QTableWidget,
    row: int,
    col: int,
    parent: QWidget,
    *,
    rows: list[dict[str, Any]],
    coin: dict[str, Any],
    on_create_bot: CreateBotCb | None = None,
    has_filter_row: bool = False,
) -> None:
    if col != 0:
        return
    if has_filter_row and data_row_index(row, has_filter_row=True) < 0:
        return
    item = table.item(row, 0)
    if item is None:
        return
    raw = item.data(Qt.ItemDataRole.UserRole)
    name = str(raw or item.text() or "").strip()
    if not name or name.startswith(_BH):
        return
    from trendalgo.device.sauce_names import is_sauce as _is_sauce_click

    if _is_sauce_click(name):
        from trendalgo.device.views.secret_sauce_study import show_secret_sauce_study

        idx = item.data(Qt.ItemDataRole.UserRole + 1)
        data = rows[int(idx)] if isinstance(idx, int) and 0 <= int(idx) < len(rows) else {}
        show_secret_sauce_study(parent, data, coin=coin, on_create_bot=on_create_bot)
        return
    show_glossary_popup(parent, name)


def _net(row: dict[str, Any]) -> float | None:
    return _as_float(row.get("net_pct"))


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
