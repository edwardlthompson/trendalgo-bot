"""Finish a Backtest All-TA worker job into page state."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel, QProgressBar

from trendalgo.device import strings as S
from trendalgo.device.backtest_notify import done_status_line
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
    bar: QProgressBar | None = None,
    persist: bool = True,
    market_context: dict[str, Any] | None = None,
    elapsed_s: float | None = None,
    data_source: str | None = None,
    cache_age_s: float | None = None,
    notify: bool = False,
) -> bool:
    """Load rows into page or show empty/error. Returns True when table should fill."""
    ctx = market_context if isinstance(market_context, dict) else None
    source = data_source
    age = cache_age_s
    if ctx is not None:
        if not source:
            source = str(ctx.get("data_source") or "") or None
        if age is None and ctx.get("cache_age_s") is not None:
            try:
                age = float(ctx["cache_age_s"])
            except (TypeError, ValueError):
                age = None
    line = done_status_line(elapsed_s=elapsed_s, data_source=source, cache_age_s=age)
    if not isinstance(rows, list) or not rows:
        empty.set_text(S.BACKTEST_NO_CANDLES_TITLE, S.BACKTEST_NO_CANDLES_BODY)
        page._show_empty()
        status.setText(line)
        _apply_market_context(page, None)
        return False
    page._sort_key = DEFAULT_SORT_KEY
    page._sort_dir = DEFAULT_SORT_DIR
    page._all_rows = sort_rows(rows, key=page._sort_key, direction=page._sort_dir)
    page._apply_view_filter()
    page._persist_prefs()
    page._market_context = ctx
    _apply_market_context(page, page._market_context)
    if persist:
        save_last_pair_backtest(
            page._root,
            page._pair.text().strip().upper(),
            page._all_rows,
            market_context=page._market_context,
        )
    page._fill_table()
    status.setText(line)
    if bar is not None:
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
    if notify and persist:
        from trendalgo.device.views.backtest_done_notify import announce_backtest_done

        announce_backtest_done(page, elapsed_s=elapsed_s)
    return True


def _apply_market_context(page: Any, raw: dict[str, Any] | None) -> None:
    pane = getattr(page, "_market_ctx", None)
    if pane is None:
        return
    if raw is None:
        pane.set_empty()
    else:
        pane.set_context(raw)


def fail_scan(page: Any, problem: QLabel, message: str) -> None:
    show_problem(problem, message)
    page._status.setText("")
    page._show_empty()
    _apply_market_context(page, None)


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
            market_context=getattr(page, "_market_context", None),
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
