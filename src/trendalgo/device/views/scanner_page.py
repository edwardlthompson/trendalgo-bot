"""Opportunity scanner: Run scan, filters, dense table, logs."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from multiprocessing.pool import AsyncResult
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.lts_scan_model import (
    filter_coins,
    load_filters,
    load_lts_rows,
    load_watchlist,
    save_filters,
    save_watchlist,
)
from trendalgo.device.rows import scan_caption
from trendalgo.device.scan_alerts import process_scan_alerts, toast_lines
from trendalgo.device.scan_job import scan_job
from trendalgo.device.scan_model import (
    ScanUnavailableError,
    progress_line,
    progress_pct,
    scan_store_path,
)
from trendalgo.device.scan_progress import clear_progress, read_progress
from trendalgo.device.scanner_schedule import clamp_interval_minutes, minutes_until, next_run_at
from trendalgo.device.scanner_share import default_scanner_export_path, export_scanner_list_png
from trendalgo.device.scanner_sort import (
    COL_SORT_KEYS,
    DEFAULT_SORT_DIR,
    DEFAULT_SORT_KEY,
    sort_coins,
)
from trendalgo.device.stores import StoreReadError, read_snapshot
from trendalgo.device.views.scanner_chart_dialog import show_scanner_chart_dialog
from trendalgo.device.views.scanner_column_filter_row import ScannerColumnFilterRow
from trendalgo.device.views.scanner_compare import show_compare_dialog
from trendalgo.device.views.scanner_filters import ScannerFilterBar
from trendalgo.device.views.scanner_results import show_results_dialog
from trendalgo.device.views.scanner_table import COLUMNS, fill_lts_table
from trendalgo.device.views.widgets import (
    EmptyState,
    TailFill,
    clear_problem,
    problem_label,
    read_only_table,
    show_problem,
)
from trendalgo.device.workers import WorkerPool
from trendalgo.scanner.snapshot import QualifiedSnapshot

POLL_MS = 250
CAPTION_MS = 30_000
TAB_QUALIFIED, TAB_WATCH, TAB_LOGS = range(3)


class ScannerPage(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        parent: QWidget | None = None,
        *,
        on_create_bot: Callable[[dict[str, str], str], str] | None = None,
        on_spark_chart: Callable[[dict[str, Any], str], None] | None = None,
        on_toast: Callable[[str, str], None] | None = None,
        on_alerts_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = ctx.root
        self._saved = ctx.databases["scanner"]
        self._candles = ctx.databases.get("candles")
        self._own = scan_store_path(ctx.root)
        self._on_create_bot = on_create_bot
        self._on_spark_chart = on_spark_chart
        self._on_toast = on_toast
        self._on_alerts_changed = on_alerts_changed
        self._pool = WorkerPool(workers=1)
        self._pending: AsyncResult[Any] | None = None
        self._compare: set[str] = set()
        self._coins: list[dict[str, Any]] = []
        self._shown: list[dict[str, Any]] = []
        self._sort_key = DEFAULT_SORT_KEY
        self._sort_dir = DEFAULT_SORT_DIR
        self._next_auto: datetime | None = None
        self._autoscan_enabled = True
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._on_auto_scan)
        self._caption_timer = QTimer(self)
        self._caption_timer.setInterval(CAPTION_MS)
        self._caption_timer.timeout.connect(self._refresh_auto_caption)

        self._filters = ScannerFilterBar()
        self._col_filters = ScannerColumnFilterRow()
        self._run = self._filters.run
        self._cancel = self._filters.cancel
        self._status = QLabel()
        self._problem = problem_label()
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        self._caption = QLabel()
        self._caption.setObjectName("hint")
        self._caption.setWordWrap(True)
        self._empty = EmptyState(S.SCANNER_EMPTY_TITLE, S.SCANNER_EMPTY_BODY)
        self._tabs = QTabBar()
        for label in (S.SCANNER_TAB_QUALIFIED, S.SCANNER_TAB_WATCH, S.SCANNER_TAB_LOGS):
            self._tabs.addTab(label)
        self._table = read_only_table(S.SCANNER_LTS_HEADERS, S.SCANNER_TITLE)
        self._table.setColumnCount(COLUMNS)
        self._col_filters.attach(self._table)
        self._table.horizontalHeader().sectionClicked.connect(self._on_header)
        self._table.horizontalHeader().sectionResized.connect(
            lambda *_a: self._col_filters.sync_control_widths(self._table)
        )
        self._logs = QPlainTextEdit()
        self._logs.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._filters)
        layout.addWidget(self._tabs)
        layout.addWidget(self._status)
        layout.addWidget(self._problem)
        layout.addWidget(self._bar)
        self._caption.hide()  # last-scan text is folded into the top filter row
        layout.addWidget(self._empty)
        layout.addWidget(self._table)
        layout.addWidget(self._logs)
        self._fill = TailFill(layout, self._table)
        saved = load_filters(self._root)
        from trendalgo.device.results_view_prefs import load_results_prefs  # noqa: PLC0415

        view = load_results_prefs(self._root)
        saved = {
            **saved,
            "heatmap_enabled": view.heatmap_enabled,
            "perfect_only": view.perfect_only,
        }
        self._filters.load(saved)
        self._col_filters.load(saved)
        self._sort_key = str(saved.get("sort_key") or DEFAULT_SORT_KEY)
        try:
            self._sort_dir = int(saved.get("sort_dir", DEFAULT_SORT_DIR))
        except (TypeError, ValueError):
            self._sort_dir = DEFAULT_SORT_DIR
        self._run.clicked.connect(lambda _checked=False: self._start())
        self._cancel.clicked.connect(lambda _checked=False: self._cancel_run())
        self._wire_filter_signals()
        self._tabs.currentChanged.connect(lambda _index: self._show_tab())
        self._filters.compare_btn.clicked.connect(lambda _c=False: self._open_compare())
        self._filters.clear_btn.clicked.connect(lambda _c=False: self._clear_compare())
        self._filters.share.clicked.connect(lambda _c=False: self._share_png())
        self.reload()
        self._schedule_autoscan(reset=True)
        self._caption_timer.start()

    def _wire_filter_signals(self) -> None:
        self._filters.exchange.currentIndexChanged.connect(lambda _i: self._on_filter())
        self._filters.signals.currentIndexChanged.connect(lambda _i: self._on_filter())
        self._filters.vol.editingFinished.connect(self._on_filter)
        self._filters.every.editingFinished.connect(self._on_filter)
        self._filters.heatmap.toggled.connect(lambda _c: self._on_filter())
        self._filters.perfect.toggled.connect(lambda _c: self._on_filter())
        for edit in (
            self._col_filters.gain_7d,
            self._col_filters.gain_30d,
            self._col_filters.best_bt,
        ):
            edit.editingFinished.connect(self._on_filter)
            edit.returnPressed.connect(self._on_filter)
        for box in (
            self._col_filters.bot_vs_bh,
            self._col_filters.chart_dist_7d,
            self._col_filters.chart_dist_30d,
            self._col_filters.health_min,
            self._col_filters.uniformity_min,
            self._col_filters.vol_accel,
            self._col_filters.vol24_min,
        ):
            box.currentIndexChanged.connect(lambda _i: self._on_filter())

    def reload(self) -> None:
        try:
            snapshot, from_pc = self._latest()
        except StoreReadError as exc:
            show_problem(self._problem, str(exc))
            return
        clear_problem(self._problem)
        self._coins = load_lts_rows(self._root)
        if not self._coins and snapshot is not None:
            from trendalgo.device.lts_scan_model import build_lts_rows

            self._coins = build_lts_rows(snapshot, enrich_charts=False)
        if snapshot is None and not self._coins:
            self._caption.clear()
            self._empty.set_text(S.SCANNER_EMPTY_TITLE, S.SCANNER_EMPTY_BODY)
        elif snapshot is not None:
            source = S.SCANNER_FROM_PC if from_pc else S.SCANNER_FROM_BOT
            self._caption.setText(f"{scan_caption(snapshot)} {source}")
            self._empty.set_text(S.SCANNER_NONE_TITLE, S.SCANNER_NONE_BODY)
        else:
            self._caption.setText(S.SCANNER_FROM_PC)
            self._empty.set_text(S.SCANNER_NONE_TITLE, S.SCANNER_NONE_BODY)
        self._refresh_auto_caption()
        self._show_tab()

    def _on_filter(self) -> None:
        self._persist_filters()
        self._status.setText(S.SCANNER_FILTERS_SAVED)
        self._schedule_autoscan(reset=True)
        self._show_tab()

    def start_scan(self) -> None:
        self._start()

    def stop_autoscan(self) -> None:
        self._autoscan_enabled = False
        self._auto_timer.stop()
        self._caption_timer.stop()
        self._cancel_run()

    def _schedule_autoscan(self, *, reset: bool) -> None:
        if not self._autoscan_enabled:
            return
        minutes = clamp_interval_minutes(self._filters.every.value())
        if reset or self._next_auto is None:
            self._next_auto = next_run_at(minutes)
        delay_ms = max(1_000, int((self._next_auto - datetime.now(tz=UTC)).total_seconds() * 1000))
        self._auto_timer.start(delay_ms)
        self._refresh_auto_caption()

    def _on_auto_scan(self) -> None:
        if not self._autoscan_enabled:
            return
        if self._pending is not None:
            self._filters.auto_status.setText(S.AUTOSCAN_PAUSED)
            self._schedule_autoscan(reset=False)
            return
        self._start()

    def _refresh_auto_caption(self) -> None:
        label = self._filters.auto_status
        parts: list[str] = []
        last = self._caption.text().strip()
        if last:
            parts.append(last)
        if not self._autoscan_enabled:
            label.setText(" · ".join(parts))
            return
        if self._pending is not None:
            parts.append(S.AUTOSCAN_PAUSED)
        elif self._next_auto is None:
            parts.append(S.AUTOSCAN_OFF)
        else:
            parts.append(S.AUTOSCAN_NEXT.format(minutes=minutes_until(self._next_auto)))
        label.setText(" · ".join(parts))

    def _on_header(self, section: int) -> None:
        key = COL_SORT_KEYS.get(section)
        if key is None:
            return
        if key == self._sort_key:
            self._sort_dir = -self._sort_dir
        else:
            self._sort_key = key
            self._sort_dir = DEFAULT_SORT_DIR
        self._persist_filters()
        self._show_tab()

    def _show_tab(self) -> None:
        tab = self._tabs.currentIndex()
        watch = set(load_watchlist(self._root))
        base = (
            [c for c in self._coins if _in_watch(c, watch)]
            if tab == TAB_WATCH
            else list(self._coins)
        )
        col = self._col_filters.dump()
        coins = filter_coins(
            base,
            exchange=self._filters.exchange.currentText(),
            min_gain_7d=(
                self._col_filters.gain_7d.value() if self._col_filters.gain_7d.value() > 0 else None
            ),
            min_gain_30d=(
                self._col_filters.gain_30d.value()
                if self._col_filters.gain_30d.value() > 0
                else None
            ),
            min_best_bt=(
                self._col_filters.best_bt.value() if self._col_filters.best_bt.value() > 0 else None
            ),
            bot_vs_bh_filter=str(col.get("bot_vs_bh_filter") or "") or None,
            chart_dist_max_7d=_opt_float(col.get("chart_dist_max_7d")),
            chart_dist_max_30d=_opt_float(col.get("chart_dist_max_30d")),
            health_min=_opt_float(col.get("health_min")),
            uniformity_min=_opt_float(col.get("uniformity_min")),
            vol_accel_filter=str(col.get("vol_accel_filter") or "") or None,
            vol24_min=_opt_float(col.get("vol24_min")),
        )
        coins = sort_coins(coins, key=self._sort_key, direction=self._sort_dir)
        self._shown = coins
        show_table = tab in (TAB_QUALIFIED, TAB_WATCH)
        show_logs = tab == TAB_LOGS
        # Always keep the table shell + column filters on Qualified/Watch so chart-dist
        # and other widen-net controls stay available even when the scan qualifies none.
        has_source = bool(base)
        show_grid = show_table
        filter_miss = show_table and has_source and not coins
        empty_scan = show_table and not has_source
        self._table.setVisible(show_grid)
        # Filters stay on the table; status carries the "no pairs" copy (not a blank page).
        self._empty.setVisible(False)
        self._col_filters.set_filters_visible(show_grid)
        self._logs.setVisible(show_logs)
        if show_logs:
            self._fill.set_target(self._logs)
            self._fill.update(True)
        else:
            self._fill.set_target(self._table)
            self._fill.update(show_grid)
        if empty_scan:
            self._status.setText(S.SCANNER_NONE_TITLE)
        elif filter_miss:
            self._status.setText(S.SCANNER_FILTER_NONE_STATUS)
        elif self._status.text() in {S.SCANNER_FILTER_NONE_STATUS, S.SCANNER_NONE_TITLE}:
            self._status.clear()
        self._filters.set_compare_pairs(self._compare)
        if show_grid:
            keep_filters = self._col_filters.row_installed(self._table)
            if not keep_filters:
                self._col_filters.prepare_for_refill()
            fill_lts_table(
                self._table,
                coins,
                compare=self._compare,
                watch=watch,
                sort_key=self._sort_key,
                sort_dir=self._sort_dir,
                heatmap=bool(self._filters.heatmap.isChecked()),
                filter_row=True,
                on_compare=self._on_compare,
                on_results=self._on_results,
                on_watch=self._on_watch,
                on_spark=self._on_spark,
            )
            self._col_filters.install_row(self._table)

    def _on_compare(self, pair: str, checked: bool) -> None:
        if checked:
            if len(self._compare) >= 2 and pair not in self._compare:
                return
            self._compare.add(pair)
        else:
            self._compare.discard(pair)
        self._filters.set_compare_pairs(self._compare)

    def _on_watch(self, pair: str, checked: bool) -> None:
        symbol = pair.split("/")[0].strip().upper() if "/" in pair else pair
        watch = load_watchlist(self._root)
        cleaned = [p for p in watch if p != pair and p != symbol]
        if checked:
            cleaned.append(pair)
        save_watchlist(self._root, cleaned)
        self._show_tab()

    def _on_results(self, coin: dict[str, Any]) -> None:
        show_results_dialog(
            self,
            coin,
            heatmap=bool(self._filters.heatmap.isChecked()),
            perfect_only=bool(self._filters.perfect.isChecked()),
            on_create_bot=self._on_create_bot,
            export_root=self._root,
        )

    def _on_spark(self, coin: dict[str, Any], window: str) -> None:
        if self._on_spark_chart is not None:
            self._on_spark_chart(coin, window)
            return
        show_scanner_chart_dialog(
            self,
            coin,
            window=window,
            candles_db=self._candles,
            price_only=True,
        )

    def _open_compare(self) -> None:
        if len(self._compare) < 2:
            show_problem(self._problem, S.SCANNER_COMPARE_NEED_TWO)
            return
        clear_problem(self._problem)
        show_compare_dialog(self, self._coins, self._compare)

    def _clear_compare(self) -> None:
        self._compare.clear()
        self._show_tab()

    def _persist_filters(self) -> None:
        payload = {**self._filters.dump(), **self._col_filters.dump()}
        payload["sort_key"] = self._sort_key
        payload["sort_dir"] = self._sort_dir
        save_filters(self._root, payload)
        from trendalgo.device.results_view_prefs import (  # noqa: PLC0415
            ResultsViewPrefs,
            load_results_prefs,
            save_results_prefs,
        )

        prior = load_results_prefs(self._root)
        save_results_prefs(
            self._root,
            ResultsViewPrefs(
                heatmap_enabled=bool(self._filters.heatmap.isChecked()),
                perfect_only=bool(self._filters.perfect.isChecked()),
                last_pair=prior.last_pair,
                results_dialog_width=prior.results_dialog_width,
                results_dialog_height=prior.results_dialog_height,
                results_dialog_maximized=prior.results_dialog_maximized,
            ),
        )

    def _latest(self) -> tuple[QualifiedSnapshot | None, bool]:
        sources = [(self._own, True)]
        if self._saved != self._own:
            sources.append((self._saved, False))
        found: list[tuple[QualifiedSnapshot, bool]] = []
        for path, from_pc in sources:
            snapshot = read_snapshot(path)
            if snapshot is not None:
                found.append((snapshot, from_pc))
        if not found:
            return None, False
        return max(found, key=lambda item: item[0].generated_at.timestamp())

    def _start(self) -> None:
        if self._pending is not None:
            return
        self._persist_filters()
        clear_problem(self._problem)
        clear_progress(self._root)
        self._pending = self._pool.submit(scan_job, self._root)
        self._filters.set_running(True)
        self._status.setText(S.SCAN_STARTING)
        self._bar.setValue(0)
        self._tabs.setCurrentIndex(TAB_LOGS)
        self._refresh_auto_caption()
        self._timer.start()

    def _poll(self) -> None:
        job = self._pending
        if job is None:
            self._timer.stop()
            return
        raw = read_progress(self._root)
        line = progress_line(raw) or S.SCAN_STARTING
        self._status.setText(line)
        self._logs.appendPlainText(line)
        pct = progress_pct(raw)
        if pct is not None:
            self._bar.setValue(pct)
        if not job.ready():
            return
        self._timer.stop()
        self._pending = None
        self._filters.set_running(False)
        self._status.clear()
        self._bar.setValue(100)
        problem = ""
        try:
            job.get(timeout=0)
        except ScanUnavailableError:
            problem = S.SCAN_UNAVAILABLE
        except Exception:
            problem = S.SCAN_FAILED
        self._tabs.setCurrentIndex(TAB_QUALIFIED)
        self.reload()
        if problem:
            show_problem(self._problem, problem)
        else:
            self._status.setText(S.SCAN_DONE)
            self._emit_scan_alerts()
        self._schedule_autoscan(reset=True)

    def _share_png(self) -> None:
        if not self._shown or not self._table.isVisible():
            QMessageBox.information(self, S.SCANNER_SHARE, S.SCANNER_SHARE_NEED_ROWS)
            return
        suggested = str(default_scanner_export_path(self._root, label="list"))
        chosen, _flt = QFileDialog.getSaveFileName(
            self, S.SCANNER_SHARE_DIALOG, suggested, S.SCANNER_SHARE_FILTER
        )
        if not chosen:
            return
        out = Path(chosen) if chosen.lower().endswith(".png") else Path(f"{chosen}.png")
        try:
            export_scanner_list_png(
                out,
                coins=self._shown,
                title=f"Scanner · {len(self._shown)} pairs",
                filters={**self._filters.dump(), **self._col_filters.dump()},
                heatmap=bool(self._filters.heatmap.isChecked()),
                sort_key=self._sort_key,
                sort_dir=self._sort_dir,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, S.SCANNER_SHARE, str(exc))
            return
        note = S.SCANNER_SHARE_DONE.format(name=out.name, path=str(out.parent))
        QMessageBox.information(self, S.SCANNER_SHARE, note)

    def _emit_scan_alerts(self) -> None:
        from trendalgo.device.scanner_alerts_store import append_log_alert

        watch = load_watchlist(self._root)
        floors = self._filters.dump()
        events, _history = process_scan_alerts(
            self._root,
            coins=self._coins,
            watchlist_pairs=watch,
            floors={
                "min_volume_usd": float(floors.get("min_volume_usd") or 0),
                "min_uniformity": float(floors.get("min_uniformity") or 0),
            },
        )
        append_log_alert(
            self._root,
            kind="scan_log",
            reason=f"Scan finished: {len(self._coins)} qualified",
        )
        if self._on_alerts_changed is not None:
            self._on_alerts_changed()
        if self._on_toast is not None:
            for title, body in toast_lines(events, self._root):
                self._on_toast(title, body)

    def _cancel_run(self) -> None:
        self._timer.stop()
        self._pending = None
        self._pool.cancel()
        self._filters.set_running(False)
        self._status.setText(S.SCAN_CANCELLED)
        self._bar.setValue(0)
        self._refresh_auto_caption()


def _in_watch(coin: dict[str, Any], watch: set[str]) -> bool:
    pair = str(coin.get("pair") or "")
    symbol = str(coin.get("symbol") or "")
    return bool(pair and pair in watch) or bool(symbol and symbol in watch)


def _opt_float(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, int | float) and not isinstance(raw, bool):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None
