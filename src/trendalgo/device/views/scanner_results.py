"""Results dialog: strategy sheet, glossary popups, one-click Create Bot, share export."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.backtest_results_ui import (
    CREATE_BOT_COL,
    SHOW_CHART_COL,
    filter_perfect_rows,
    heat_for_rows,
    row_cells,
    skip_tooltip,
)
from trendalgo.device.icons import nav_icon
from trendalgo.device.results_view_prefs import load_results_prefs, save_results_prefs
from trendalgo.device.scanner_heat import fg_for_bg
from trendalgo.device.scanner_plan_prefill import plan_prefill_from_scanner_row
from trendalgo.device.scanner_share import default_scanner_export_path, export_strategy_sheet_png
from trendalgo.device.scanner_signal_sets import BT_SET_ALL_TA, is_three_commas_indicator
from trendalgo.device.table_fit import fit_table_columns
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.glossary_popup import glossary_tooltip, show_glossary_popup

_COLUMNS = S.BACKTEST_RESULT_HEADERS
_BH = "B&H"
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
    from trendalgo.device.sauce_names import is_sauce

    if is_sauce(text):
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
    rows = strategy_sheet_rows(coin, perfect_only=perfect_only)
    body = QWidget()
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(0, 0, 0, 0)
    if not rows:
        body_layout.addWidget(QLabel(S.SCANNER_RESULTS_EMPTY))
    else:
        table = QTableWidget(len(rows), len(_COLUMNS))
        table.setHorizontalHeaderLabels(list(_COLUMNS))
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        heat = heat_for_rows(rows) if heatmap else {}
        theme = colors_for(active_mode())
        bh_bg = theme["secondaryContainer"]
        bh_fg = theme["onSecondaryContainer"]
        ss_bg = theme["primaryContainer"]
        ss_fg = theme["onPrimaryContainer"]
        signal_set = str(coin.get("bt_signal_set") or "")
        for r, row in enumerate(rows):
            name = str(row.get("indicator") or "").strip()
            is_bh = name == _BH
            from trendalgo.device.sauce_names import is_sauce as _is_sauce

            is_sauce = _is_sauce(name)
            is_baseline = name in {_BH, "Oracle max"}
            values = row_cells(row, is_bh=is_bh)
            for c, text in enumerate(values):
                label = (
                    indicator_display_label(
                        name,
                        bt_signal_set=signal_set,
                        is_bh=is_bh,
                    )
                    if c == 0
                    else text
                )
                item = QTableWidgetItem(label)
                if c == 0 and not is_bh:
                    if is_sauce:
                        tip = S.SECRET_SAUCE_FORMULA
                        dossier = row.get("heartbeat_dossier")
                        if isinstance(dossier, dict) and dossier.get("formula_en"):
                            tip = str(dossier.get("formula_en"))
                    else:
                        tip = glossary_tooltip(name)
                        skip = skip_tooltip(row)
                        if skip:
                            tip = f"{skip}\n\n{tip}" if tip else skip
                    if tip:
                        item.setToolTip(tip)
                    item.setData(Qt.ItemDataRole.UserRole, name)
                    item.setData(Qt.ItemDataRole.UserRole + 1, r)
                    item.setForeground(QColor(theme["primary"]))
                    font = item.font()
                    font.setUnderline(True)
                    item.setFont(font)
                if is_baseline or is_sauce:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                color = heat.get(c, [None] * len(rows))[r] if heatmap else None
                if color:
                    item.setBackground(QColor(color))
                    item.setForeground(QColor(fg_for_bg(color)))
                elif is_bh:
                    item.setBackground(QColor(bh_bg))
                    item.setForeground(QColor(bh_fg))
                elif is_sauce:
                    item.setBackground(QColor(ss_bg))
                    item.setForeground(QColor(ss_fg))
                table.setItem(r, c, item)
            _show_chart_cell(table, r, row, coin=coin, parent=dialog)
            _create_bot_cell(
                table,
                r,
                row,
                is_bh=is_bh and not is_sauce,
                pair=pair,
                status=status,
                on_create_bot=on_create_bot,
            )
        table.cellClicked.connect(
            lambda row_i, col: _on_indicator_click(
                table, row_i, col, dialog, rows=rows, coin=coin, on_create_bot=on_create_bot
            )
        )
        fit_table_columns(table)
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
    share.setEnabled(bool(rows) and export_root is not None)

    def _share(_checked: bool = False) -> None:
        if export_root is None or not rows:
            return
        suggested = str(default_scanner_export_path(export_root, label=symbol or "pair"))
        chosen, _flt = QFileDialog.getSaveFileName(
            dialog, S.SCANNER_SHARE_DIALOG, suggested, S.SCANNER_SHARE_FILTER
        )
        if not chosen:
            return
        out = Path(chosen) if chosen.lower().endswith(".png") else Path(f"{chosen}.png")
        try:
            export_strategy_sheet_png(out, pair=pair or symbol, rows=rows, heatmap=heatmap)
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


def _on_indicator_click(
    table: QTableWidget,
    row: int,
    col: int,
    parent: QWidget,
    *,
    rows: list[dict[str, Any]],
    coin: dict[str, Any],
    on_create_bot: CreateBotCb | None = None,
) -> None:
    if col != 0:
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


def _show_chart_cell(
    table: QTableWidget,
    row: int,
    strategy: dict[str, Any],
    *,
    coin: dict[str, Any],
    parent: QWidget,
) -> None:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(2, 2, 2, 2)
    btn = QPushButton(S.BACKTEST_SHOW_CHART)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    name = str(strategy.get("indicator") or "").strip()
    from trendalgo.device.sauce_names import is_sauce_lab

    pending = is_sauce_lab(name) and bool(strategy.get("ss_lab_pending"))
    btn.setEnabled(not pending)

    def _open(_checked: bool = False, data: dict[str, Any] = strategy) -> None:
        from trendalgo.device.views.scanner_chart_dialog import show_scanner_chart_dialog

        show_scanner_chart_dialog(
            parent,
            coin,
            window="30d",
            price_only=str(data.get("indicator") or "").strip() == _BH,
            strategy_row=None if str(data.get("indicator") or "").strip() == _BH else data,
        )

    btn.clicked.connect(_open)
    layout.addWidget(btn)
    table.setCellWidget(row, SHOW_CHART_COL, host)


def _create_bot_cell(
    table: QTableWidget,
    row: int,
    strategy: dict[str, Any],
    *,
    is_bh: bool,
    pair: str,
    status: QLabel,
    on_create_bot: CreateBotCb | None,
) -> None:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(2, 2, 2, 2)
    if is_bh or on_create_bot is None:
        layout.addWidget(QLabel("—"))
    else:
        btn = QPushButton(S.SCANNER_CREATE_BOT)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        def _create(_checked: bool = False, row_data: dict[str, Any] = strategy) -> None:
            fields, note = plan_prefill_from_scanner_row(row_data, pair=pair)
            if fields is None:
                status.setText(note)
                return
            message = on_create_bot(fields, note)
            if message:
                status.setText(message)
            elif note:
                status.setText(note)

        btn.clicked.connect(_create)
        layout.addWidget(btn)
    table.setCellWidget(row, CREATE_BOT_COL, host)


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
