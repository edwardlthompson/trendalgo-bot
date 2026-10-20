"""Backtest tab: pair picker, All-TA scan, sortable/filterable results."""

from __future__ import annotations

from collections.abc import Callable
from multiprocessing.pool import AsyncResult
from typing import Any, cast

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.backtest_results_ui import filter_perfect_rows
from trendalgo.device.backtest_row_filter import filter_rows
from trendalgo.device.backtest_sort import (
    COL_SORT_KEYS,
    DEFAULT_SORT_DIR,
    DEFAULT_SORT_KEY,
    sort_rows,
)
from trendalgo.device.context import DeviceContext
from trendalgo.device.flow_layout import FlowLayout
from trendalgo.device.icons import nav_icon
from trendalgo.device.pair_scan_partial import clear_partial_rows, read_partial_rows
from trendalgo.device.pair_scan_progress import clear_progress, progress_line, read_progress
from trendalgo.device.pair_strategy_scan_job import pair_strategy_scan_job
from trendalgo.device.results_view_prefs import (
    ResultsViewPrefs,
    load_results_prefs,
    save_results_prefs,
)
from trendalgo.device.sauce_names import is_sauce
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.backtest_column_filter_row import FILTER_ROW, BacktestColumnFilterRow
from trendalgo.device.views.backtest_page_job import (
    apply_partial_rows,
    apply_scan_result,
    fail_scan,
    fill_or_empty,
)
from trendalgo.device.views.backtest_share_dialog import run_backtest_share_dialog
from trendalgo.device.views.glossary_popup import show_glossary_popup
from trendalgo.device.views.searchable_picker import pair_picker
from trendalgo.device.views.widgets import (
    EmptyState,
    TailFill,
    clear_problem,
    mark_primary,
    problem_label,
    read_only_table,
    show_problem,
)
from trendalgo.device.workers import WorkerPool

POLL_MS = 200
FILTER_DEBOUNCE_MS = 2000
_BH = "B&H"
CreateBotCb = Callable[[dict[str, str]], None]


class BacktestPage(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        pool: WorkerPool,
        *,
        on_open_plan: CreateBotCb | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = ctx.root
        self._pool = pool
        self._on_open_plan = on_open_plan
        self._pending: AsyncResult[Any] | None = None
        self._rows: list[dict[str, Any]] = []
        self._all_rows: list[dict[str, Any]] = []
        self._sort_key = DEFAULT_SORT_KEY
        self._sort_dir = DEFAULT_SORT_DIR
        self._last_log = ""
        self._last_partial_n = -1
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(FILTER_DEBOUNCE_MS)
        self._filter_timer.timeout.connect(self._apply_debounced_filters)
        prefs = load_results_prefs(self._root)

        self._pair = pair_picker()
        pair_w = QFontMetrics(self._pair.font()).horizontalAdvance("XXXX/XXXX") + 56
        self._pair.setMinimumWidth(pair_w)
        if prefs.last_pair and "/" in prefs.last_pair:
            self._pair.setText(prefs.last_pair)
        self._run = mark_primary(QPushButton(S.BACKTEST_RUN))
        self._run.setDefault(True)
        self._cancel = QPushButton(S.CANCEL)
        self._cancel.setEnabled(False)
        self._share = QToolButton()
        self._share.setObjectName("shareButton")
        self._share.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._share.setIcon(nav_icon("share", colors_for(active_mode())["onSurfaceVariant"], 20))
        self._share.setToolTip(S.BACKTEST_SHARE_TIP)
        self._share.setAccessibleName(S.BACKTEST_SHARE)
        self._heatmap = QCheckBox(S.SCANNER_COLOR_RANKS)
        self._heatmap.setChecked(prefs.heatmap_enabled)
        self._perfect = QCheckBox(S.BACKTEST_PERFECT_ONLY)
        self._perfect.setChecked(prefs.perfect_only)
        self._perfect.setToolTip(S.BACKTEST_PERFECT_HELP)
        self._derive = QPushButton(S.BACKTEST_DERIVE_RULE)
        self._derive.setToolTip(S.BACKTEST_DERIVE_RULE_HELP)
        self._derive.clicked.connect(lambda _c=False: self._derive_oracle_rule())
        self._heatmap.toggled.connect(lambda _c: self._on_view_toggle())
        self._perfect.toggled.connect(lambda _c: self._on_view_toggle())
        self._status = QLabel()
        self._status.setObjectName("hint")
        self._status.setWordWrap(True)
        self._problem = problem_label()
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        self._empty = EmptyState(S.BACKTEST_EMPTY_TITLE, S.BACKTEST_EMPTY_BODY)
        self._table = read_only_table(S.BACKTEST_RESULT_HEADERS, S.BACKTEST_TITLE)
        self._filters = BacktestColumnFilterRow()
        self._filters.attach(self._table)
        for control in self._filters._by_col.values():
            cast(QLineEdit, control).textChanged.connect(lambda _t="": self._on_filters_changed())
        self._table.horizontalHeader().sectionClicked.connect(self._on_header)
        self._table.cellClicked.connect(self._on_cell_clicked)
        self._create_note = QLabel()
        self._create_note.setObjectName("hint")
        self._create_note.setWordWrap(True)

        toolbar = FlowLayout(margin=0, h_spacing=8, v_spacing=4)
        pair_label = QLabel(S.BACKTEST_PAIR)
        for widget in (
            pair_label,
            self._pair,
            self._run,
            self._cancel,
            self._share,
            self._heatmap,
            self._perfect,
            self._derive,
        ):
            toolbar.addWidget(widget)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self._status)
        layout.addWidget(self._problem)
        layout.addWidget(self._bar)
        layout.addWidget(self._empty)
        layout.addWidget(self._table, 1)
        layout.addWidget(self._create_note)
        self._fill = TailFill(layout, self._table)
        self._fill.update(False)

        self._run.clicked.connect(lambda _c=False: self._start())
        self._cancel.clicked.connect(lambda _c=False: self._cancel_run())
        self._share.clicked.connect(lambda _c=False: self._share_png())
        if not self._restore_last_backtest():
            self._show_empty()

    def _restore_last_backtest(self) -> bool:
        from trendalgo.device.last_pair_backtest import load_last_pair_backtest

        saved = load_last_pair_backtest(self._root)
        if saved is None:
            return False
        pair, rows = saved
        self._pair.setText(pair)
        return apply_scan_result(
            self,
            rows,
            problem=self._problem,
            empty=self._empty,
            status=self._status,
            bar=self._bar,
            persist=False,
        )

    def _start(self) -> None:
        if self._pending is not None:
            return
        pair = self._pair.text().strip().upper()
        if "/" not in pair or len(pair.split("/", 1)[0].strip()) < 1:
            show_problem(self._problem, S.BACKTEST_PAIR_REQUIRED)
            return
        clear_problem(self._problem)
        clear_progress(self._root)
        clear_partial_rows(self._root)
        self._last_log = ""
        self._last_partial_n = -1
        self._rows = []
        self._all_rows = []
        self._filters.prepare_for_refill()
        self._table.setRowCount(0)
        self._show_running()
        self._pending = self._pool.submit(pair_strategy_scan_job, self._root, pair)
        self._status.setText(S.BACKTEST_RUNNING)
        self._timer.start()

    def _poll(self) -> None:
        raw = read_progress(self._root)
        line = progress_line(raw)
        if line and line != self._last_log:
            self._last_log = line
            self._status.setText(line)
        job = self._pending
        if raw:
            done = int(raw.get("done") or 0)
            total = max(1, int(raw.get("total") or 1))
            pct = int(100 * done / total)
            # Never paint 100% until the worker finishes and results are sorted.
            if job is not None and not job.ready():
                pct = min(99, pct)
            self._bar.setValue(min(100, pct))
        partial = read_partial_rows(self._root)
        if partial is not None and len(partial) != self._last_partial_n:
            self._last_partial_n = len(partial)
            apply_partial_rows(self, partial)
        if job is None:
            self._timer.stop()
            return
        if not job.ready():
            return
        self._timer.stop()
        self._pending = None
        self._set_running(False)
        clear_partial_rows(self._root)
        try:
            rows = job.get(timeout=0)
        except ValueError as exc:
            fail_scan(self, self._problem, str(exc) or S.BACKTEST_PAIR_REQUIRED)
            return
        except Exception as exc:
            detail = str(exc).strip()
            fail_scan(
                self,
                self._problem,
                f"{S.BACKTEST_FAILED}" + (f" ({detail})" if detail else ""),
            )
            return
        apply_scan_result(
            self, rows, problem=self._problem, empty=self._empty, status=self._status, bar=self._bar
        )

    def _cancel_run(self) -> None:
        self._timer.stop()
        self._pending = None
        self._pool.cancel()
        self._set_running(False)
        self._status.setText(S.BACKTEST_CANCELLED)

    def _share_png(self) -> None:
        rows = self._rows if self._table.isVisible() else []
        note = run_backtest_share_dialog(
            self,
            root=self._root,
            pair=self._pair.text().strip().upper() or "PAIR",
            rows=rows,
            filters=self._filters.dump() if rows else {},
            heatmap=bool(self._heatmap.isChecked()),
            sort_key=self._sort_key,
            sort_dir=self._sort_dir,
        )
        if note:
            self._create_note.setText(note)

    def _on_header(self, section: int) -> None:
        key = COL_SORT_KEYS.get(section)
        if key is None or not self._all_rows:
            return
        if key == self._sort_key:
            self._sort_dir = -self._sort_dir
        else:
            self._sort_key = key
            self._sort_dir = 1 if key in ("indicator", "timeframe", "params") else DEFAULT_SORT_DIR
        self._all_rows = sort_rows(self._all_rows, key=self._sort_key, direction=self._sort_dir)
        self._refresh_rows()

    def _on_filters_changed(self) -> None:
        # Restart debounce so multi-digit entry is not applied mid-typing.
        self._filter_timer.start()

    def _apply_debounced_filters(self) -> None:
        if self._all_rows:
            self._refresh_rows()

    def _on_view_toggle(self) -> None:
        self._persist_prefs()
        if self._all_rows:
            self._refresh_rows()

    def _refresh_rows(self) -> None:
        self._apply_view_filter()
        self._fill_table()

    def _apply_view_filter(self) -> None:
        rows = (
            filter_perfect_rows(self._all_rows)
            if self._perfect.isChecked()
            else list(self._all_rows)
        )
        self._rows = filter_rows(rows, self._filters.dump())

    def _persist_prefs(self) -> None:
        prior = load_results_prefs(self._root)
        save_results_prefs(
            self._root,
            ResultsViewPrefs(
                heatmap_enabled=bool(self._heatmap.isChecked()),
                perfect_only=bool(self._perfect.isChecked()),
                last_pair=self._pair.text().strip().upper() or "BTC/USD",
                results_dialog_width=prior.results_dialog_width,
                results_dialog_height=prior.results_dialog_height,
                results_dialog_maximized=prior.results_dialog_maximized,
            ),
        )

    def _on_cell_clicked(self, row: int, col: int) -> None:
        data_row = row - (FILTER_ROW + 1)
        if col != 0 or data_row < 0 or data_row >= len(self._rows):
            return
        data = self._rows[data_row]
        name = str(data.get("indicator") or "").strip()
        if not name or name == _BH or name.startswith(_BH):
            return
        if is_sauce(name):
            from trendalgo.device.views.secret_sauce_study import show_secret_sauce_study

            show_secret_sauce_study(
                self,
                data,
                coin={"symbol": data.get("symbol"), "pair": self._pair.text().strip().upper()},
                on_create_bot=self._sauce_create_bot,
            )
            return
        show_glossary_popup(self, name)

    def _sauce_create_bot(self, prefill: dict[str, str], _pair: str) -> str:
        if self._on_open_plan is None:
            return ""
        self._on_open_plan(prefill)
        return S.SECRET_SAUCE_CREATE_BOT

    def _derive_oracle_rule(self) -> None:
        from trendalgo.device.sauce_names import SAUCE_LAB, is_sauce_lab
        from trendalgo.device.scanner_alerts_store import append_log_alert
        from trendalgo.device.views.secret_sauce_study import show_secret_sauce_study

        rows = self._all_rows or self._rows
        sauce = next((r for r in rows if is_sauce_lab(r.get("indicator"))), None)
        if sauce is None:
            sauce = next((r for r in rows if str(r.get("indicator") or "") == SAUCE_LAB), None)
        if sauce is not None and isinstance(sauce.get("heartbeat_dossier"), dict):
            show_secret_sauce_study(
                self,
                sauce,
                coin={"symbol": sauce.get("symbol"), "pair": self._pair.text().strip().upper()},
                on_create_bot=self._sauce_create_bot,
            )
            return
        QMessageBox.information(
            self,
            S.BACKTEST_DERIVE_RULE,
            S.SECRET_SAUCE_STUDY_EMPTY,
        )
        if sauce is None:
            append_log_alert(
                self._root,
                kind="backtest_log",
                reason="Secret Sauce not in results — re-run All-TA to mine per-coin heartbeat.",
            )

    def _fill_table(self) -> None:
        fill_or_empty(self)

    def _show_empty(self) -> None:
        self._empty.show()
        self._table.hide()
        self._fill.update(False)
        self._set_running(False)

    def _show_running(self) -> None:
        self._empty.hide()
        self._table.hide()
        self._fill.update(False)
        self._set_running(True)
        self._bar.setValue(0)

    def _set_running(self, running: bool) -> None:
        self._run.setEnabled(not running)
        self._cancel.setEnabled(running)
        self._pair.setEnabled(not running)
        self._share.setEnabled(not running)
