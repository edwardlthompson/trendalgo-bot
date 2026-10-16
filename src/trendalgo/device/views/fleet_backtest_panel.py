"""Fleet backtest panel: pass-1 TA sweep with progress and top-10 vs buy & hold."""

from __future__ import annotations

from collections.abc import Callable
from multiprocessing.pool import AsyncResult
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.fleet_backtest_job import fleet_backtest_job
from trendalgo.device.fleet_backtest_model import (
    FleetBacktestError,
    fleet_data_dir,
    plan_prefill_from_row,
    progress_line,
    top10_table_rows,
    validate_fleet_backtest,
)
from trendalgo.device.fleet_progress import clear_progress, read_progress
from trendalgo.device.views.searchable_picker import pair_picker
from trendalgo.device.views.widgets import (
    EmptyState,
    TailFill,
    clear_problem,
    field,
    fill_table,
    mark_primary,
    problem_label,
    read_only_table,
    section_title,
    show_problem,
)
from trendalgo.device.workers import WorkerPool

POLL_MS = 250


class FleetBacktestPanel(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        pool: WorkerPool,
        *,
        on_open_plan: Callable[[dict[str, str]], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = ctx.root
        self._data_dir = fleet_data_dir(ctx.root)
        self._pool = pool
        self._on_open_plan = on_open_plan
        self._pending: AsyncResult[Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._selected_row: dict[str, Any] | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)

        self._exchange = QLineEdit("kraken")
        self._pair = pair_picker()
        self._stake = QLineEdit("1000")
        self._run = mark_primary(QPushButton(S.FLEET_BACKTEST_RUN))
        self._run.clicked.connect(lambda _checked=False: self._start())
        self._cancel = QPushButton(S.CANCEL)
        self._cancel.setEnabled(False)
        self._cancel.clicked.connect(lambda _checked=False: self._cancel_run())
        self._create_bot = QPushButton(S.FLEET_CREATE_BOT)
        self._create_bot.setEnabled(False)
        self._create_bot.clicked.connect(lambda _checked=False: self._create_bot_from_row())
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.hide()
        self._status = QLabel()
        self._problem = problem_label()
        self._note = QLabel()
        self._note.setObjectName("hint")
        self._note.setWordWrap(True)
        self._note.setText(S.FLEET_BACKTEST_NOTE)
        self._empty = EmptyState(S.FLEET_BACKTEST_EMPTY_TITLE, S.FLEET_BACKTEST_EMPTY_BODY)
        self._bh = QLabel()
        self._results_title = section_title(S.FLEET_BACKTEST_TOP_TITLE)
        self._results = read_only_table(S.FLEET_BACKTEST_TOP_HEADERS, S.FLEET_BACKTEST_TOP_TITLE)
        self._results.itemSelectionChanged.connect(self._on_row_selected)

        inputs = QHBoxLayout()
        inputs.addWidget(field(S.FLEET_EXCHANGE, self._exchange), 1)
        inputs.addWidget(field(S.BACKTEST_PAIR, self._pair, S.BACKTEST_PAIR_HELP), 1)
        inputs.addWidget(field(S.FLEET_STAKE, self._stake, S.FLEET_STAKE_HELP), 1)
        actions = QHBoxLayout()
        actions.addWidget(self._run)
        actions.addWidget(self._cancel)
        actions.addWidget(self._create_bot)
        actions.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._note)
        layout.addLayout(inputs)
        layout.addLayout(actions)
        layout.addWidget(self._progress)
        layout.addWidget(self._status)
        layout.addWidget(self._problem)
        layout.addWidget(self._empty)
        layout.addWidget(self._bh)
        layout.addWidget(self._results_title)
        layout.addWidget(self._results)
        self._fill = TailFill(layout, self._results)
        self._clear_results()

    def _clear_results(self) -> None:
        self._last_result = None
        self._selected_row = None
        self._create_bot.setEnabled(False)
        self._bh.hide()
        self._results_title.hide()
        self._results.hide()
        self._empty.show()
        self._fill.update(False)

    def _set_running(self, running: bool) -> None:
        self._run.setEnabled(not running)
        self._cancel.setEnabled(running)

    def _start(self) -> None:
        request, problems = validate_fleet_backtest(
            exchange_id=self._exchange.text(),
            pair=self._pair.text(),
            stake=self._stake.text(),
        )
        if request is None:
            show_problem(self._problem, " ".join(problems))
            return
        clear_problem(self._problem)
        clear_progress(self._root)
        self._clear_results()
        self._progress.setValue(0)
        self._progress.show()
        job = self._pool.submit(
            fleet_backtest_job,
            self._root,
            self._data_dir,
            request.exchange_id,
            request.pair,
            request.stake_usd,
        )
        self._pending = job
        self._set_running(True)
        self._status.setText(S.FLEET_BACKTEST_RUNNING)
        self._timer.start()

    def _poll(self) -> None:
        snap = read_progress(self._root)
        if snap:
            pct = int(snap.get("progress_pct") or 0)
            self._progress.setValue(max(0, min(100, pct)))
            line = progress_line(snap)
            if line:
                self._status.setText(line)
        if self._pending is None:
            return
        if not self._pending.ready():
            return
        self._timer.stop()
        job = self._pending
        self._pending = None
        self._set_running(False)
        self._progress.hide()
        try:
            result = job.get(timeout=0)
        except FleetBacktestError as exc:
            self._status.clear()
            show_problem(self._problem, str(exc))
            return
        except Exception:
            self._status.clear()
            show_problem(self._problem, S.FLEET_BACKTEST_FAILED)
            return
        self._show_result(result)

    def _show_result(self, result: dict[str, Any]) -> None:
        self._last_result = result
        top10 = result.get("top10") or []
        buy_hold = result.get("buy_and_hold")
        if isinstance(buy_hold, dict) and buy_hold.get("net_profit") is not None:
            self._bh.setText(
                S.FLEET_BUY_HOLD.format(net=f"${float(buy_hold['net_profit']):,.2f}"),
            )
            self._bh.show()
        else:
            self._bh.hide()
        rows = top10_table_rows(top10, buy_hold if isinstance(buy_hold, dict) else None)
        fill_table(self._results, rows)
        self._status.setText(S.FLEET_BACKTEST_DONE)
        has_rows = bool(rows)
        self._empty.setVisible(not has_rows)
        self._results_title.setVisible(has_rows)
        self._results.setVisible(has_rows)
        self._fill.update(has_rows)
        if has_rows:
            self._results.selectRow(0)
            self._on_row_selected()

    def _on_row_selected(self) -> None:
        row_idx = self._results.currentRow()
        top10 = (self._last_result or {}).get("top10") or []
        if 0 <= row_idx < len(top10):
            self._selected_row = top10[row_idx]
            self._create_bot.setEnabled(self._on_open_plan is not None)
        else:
            self._selected_row = None
            self._create_bot.setEnabled(False)

    def _create_bot_from_row(self) -> None:
        if self._on_open_plan is None or self._selected_row is None or self._last_result is None:
            return
        stake = float(self._last_result.get("stake_usd") or 0)
        pair = str(self._last_result.get("pair") or self._pair.text())
        fields, note = plan_prefill_from_row(self._selected_row, pair=pair, stake_usd=stake)
        if fields is None:
            self._status.setText(note or S.FLEET_CREATE_BOT_BLOCKED)
            return
        self._on_open_plan(fields)
        self._status.setText(S.FLEET_CREATE_BOT_SENT)

    def _cancel_run(self) -> None:
        self._timer.stop()
        self._pending = None
        self._pool.cancel()
        self._set_running(False)
        self._progress.hide()
        self._status.setText(S.BACKTEST_CANCELLED)
