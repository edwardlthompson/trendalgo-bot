"""Finish a Backtest All-TA worker job into page state."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel, QProgressBar

from trendalgo.device import strings as S
from trendalgo.device.backtest_sort import DEFAULT_SORT_DIR, DEFAULT_SORT_KEY, sort_rows
from trendalgo.device.last_pair_backtest import save_last_pair_backtest
from trendalgo.device.views.widgets import show_problem


def apply_partial_rows(page: Any, rows: object) -> None:
    """Live ranked snapshot while All-TA is still running (no persist / no 100%)."""
    if not isinstance(rows, list) or not rows:
        return
    page._sort_key = DEFAULT_SORT_KEY
    page._sort_dir = DEFAULT_SORT_DIR
    page._all_rows = sort_rows(rows, key=page._sort_key, direction=page._sort_dir)
    page._apply_view_filter()
    page._fill_table()
    page._empty.hide()
    page._table.show()
    page._fill.update(True)


def apply_scan_result(
    page: Any,
    rows: object,
    *,
    problem: QLabel,
    empty: Any,
    status: QLabel,
    bar: QProgressBar,
    persist: bool = True,
) -> bool:
    """Load rows into page or show empty/error. Returns True when table should fill."""
    if not isinstance(rows, list) or not rows:
        empty.set_text(S.BACKTEST_NO_CANDLES_TITLE, S.BACKTEST_NO_CANDLES_BODY)
        page._show_empty()
        status.setText(S.BACKTEST_DONE)
        return False
    page._sort_key = DEFAULT_SORT_KEY
    page._sort_dir = DEFAULT_SORT_DIR
    page._all_rows = sort_rows(rows, key=page._sort_key, direction=page._sort_dir)
    page._apply_view_filter()
    page._persist_prefs()
    if persist:
        save_last_pair_backtest(
            page._root,
            page._pair.text().strip().upper(),
            page._all_rows,
        )
    page._fill_table()
    status.setText(S.BACKTEST_DONE)
    bar.setValue(100)
    if persist:
        try:
            from trendalgo.device.scanner_alerts_store import append_log_alert

            pair = page._pair.text().strip().upper()
            append_log_alert(
                page._root,
                kind="backtest_log",
                reason=f"All-TA finished: {len(page._all_rows)} rows for {pair}",
                pair=pair,
                symbol=pair.split("/", 1)[0] if "/" in pair else pair,
            )
        except (OSError, ValueError, TypeError, ImportError):
            pass
    return True


def fail_scan(page: Any, problem: QLabel, message: str) -> None:
    show_problem(problem, message)
    page._status.setText("")
    page._show_empty()


def fill_or_empty(page: Any) -> None:
    """Fill results table, or show empty state when filters hide every row."""
    if page._rows:
        from trendalgo.device.views.backtest_table_fill import fill_backtest_table

        fill_backtest_table(
            page._table,
            page._rows,
            pair=page._pair.text().strip().upper(),
            heatmap=bool(page._heatmap.isChecked()),
            sort_key=page._sort_key,
            sort_dir=page._sort_dir,
            filter_row=page._filters,
            on_open_plan=page._on_open_plan,
            on_note=page._create_note.setText,
        )
        page._empty.hide()
        page._table.show()
        page._fill.update(True)
        return
    page._filters.prepare_for_refill()
    page._table.setRowCount(0)
    if page._all_rows and (page._perfect.isChecked() or page._filters.dump()):
        page._empty.set_text(
            S.BACKTEST_PERFECT_ONLY if page._perfect.isChecked() else S.BACKTEST_TITLE,
            "No strategies match the current filters.",
        )
        page._empty.show()
        page._table.hide()
        page._fill.update(False)
