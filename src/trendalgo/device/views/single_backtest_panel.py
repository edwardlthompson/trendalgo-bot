"""Single-indicator backtest form (saved candles on this PC)."""

from __future__ import annotations

from multiprocessing.pool import AsyncResult
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.backtest_model import (
    BacktestRequest,
    missing_candles_text,
    summary_rows,
    validate_request,
)
from trendalgo.device.context import DeviceContext
from trendalgo.device.fields import TIMEFRAMES
from trendalgo.device.jobs import NoCandlesError, backtest_job, load_candles
from trendalgo.device.rows import backtest_trade_rows
from trendalgo.device.views.candle_chart import CandleChart
from trendalgo.device.views.searchable_picker import indicator_picker, pair_picker
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

POLL_MS = 100


class SingleBacktestPanel(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        pool: WorkerPool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._candles = ctx.databases["candles"]
        self._pool = pool
        self._pending: tuple[AsyncResult[Any], BacktestRequest] | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)

        self._pair = pair_picker()
        self._timeframe = QComboBox()
        self._timeframe.addItems(list(TIMEFRAMES))
        self._indicator = indicator_picker()
        self._stop = QLineEdit("5")
        self._run = mark_primary(QPushButton(S.BACKTEST_RUN))
        self._run.setDefault(True)
        self._run.clicked.connect(lambda _checked=False: self._start())
        self._cancel = QPushButton(S.CANCEL)
        self._cancel.setEnabled(False)
        self._cancel.clicked.connect(lambda _checked=False: self._cancel_run())
        self._status = QLabel()
        self._problem = problem_label()
        self._empty = EmptyState(S.BACKTEST_EMPTY_TITLE, S.BACKTEST_EMPTY_BODY)
        self._summary = QLabel()
        self._chart = CandleChart()
        self._chart.hide()
        self._trades_title = section_title(S.BACKTEST_TRADES_TITLE)
        self._trades = read_only_table(S.BACKTEST_TRADE_HEADERS, S.BACKTEST_TRADES_TITLE)

        top = Qt.AlignmentFlag.AlignTop
        inputs = QHBoxLayout()
        inputs.addWidget(field(S.BACKTEST_PAIR, self._pair, S.BACKTEST_PAIR_HELP), 1, top)
        inputs.addWidget(field(S.BACKTEST_TIMEFRAME, self._timeframe), 1, top)
        inputs.addWidget(field(S.BACKTEST_INDICATOR, self._indicator), 1, top)
        inputs.addWidget(field(S.BACKTEST_STOP, self._stop, S.BACKTEST_STOP_HELP), 1, top)
        actions = QHBoxLayout()
        actions.addWidget(self._run)
        actions.addWidget(self._cancel)
        actions.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(inputs)
        layout.addLayout(actions)
        layout.addWidget(self._status)
        layout.addWidget(self._problem)
        layout.addWidget(self._empty)
        layout.addWidget(self._summary)
        layout.addWidget(self._chart)
        layout.addWidget(self._trades_title)
        layout.addWidget(self._trades)
        self._fill = TailFill(layout, self._trades)
        self._clear_result()

    def _clear_result(self) -> None:
        self._empty.hide()
        self._summary.hide()
        self._chart.hide()
        self._trades_title.hide()
        self._trades.hide()
        self._fill.update(False)

    def _set_running(self, running: bool) -> None:
        self._run.setEnabled(not running)
        self._cancel.setEnabled(running)

    def _start(self) -> None:
        request, problems = validate_request(
            pair=self._pair.text(),
            timeframe=self._timeframe.currentText(),
            indicator=self._indicator.text(),
            trailing_stop=self._stop.text(),
        )
        if request is None:
            show_problem(self._problem, " ".join(problems))
            return
        clear_problem(self._problem)
        job = self._pool.submit(
            backtest_job,
            self._candles,
            request.pair,
            request.timeframe,
            request.indicator,
            request.trailing_stop_pct,
        )
        self._pending = (job, request)
        self._set_running(True)
        self._status.setText(S.BACKTEST_RUNNING)
        self._clear_result()
        self._timer.start()

    def _poll(self) -> None:
        if self._pending is None:
            self._timer.stop()
            return
        job, request = self._pending
        if not job.ready():
            return
        self._timer.stop()
        self._pending = None
        self._set_running(False)
        try:
            result = job.get(timeout=0)
        except NoCandlesError:
            self._status.clear()
            self._empty.set_text(
                S.BACKTEST_NO_CANDLES_TITLE,
                missing_candles_text(request.pair, request.timeframe),
            )
            self._empty.show()
            return
        except Exception:
            self._status.clear()
            show_problem(self._problem, S.BACKTEST_FAILED)
            return
        self._show_result(result)

    def _show_result(self, result: dict[str, Any]) -> None:
        self._status.setText(S.BACKTEST_DONE)
        self._summary.setText(
            "\n".join(f"{label}: {value}" for label, value in summary_rows(result)),
        )
        trades = backtest_trade_rows(result["trades"])
        fill_table(self._trades, trades)
        self._summary.show()
        try:
            frame = load_candles(
                self._candles,
                pair=self._pair.text().strip().upper(),
                timeframe=self._timeframe.currentText(),
            )
            self._chart.set_data(frame, result["trades"])
            self._chart.show()
        except NoCandlesError:
            self._chart.clear()
        has_trades = bool(trades)
        if not has_trades:
            self._empty.set_text(S.BACKTEST_NO_TRADES_TITLE, S.BACKTEST_NO_TRADES_BODY)
        self._empty.setVisible(not has_trades)
        self._trades_title.setVisible(has_trades)
        self._trades.setVisible(has_trades)
        self._fill.update(has_trades)

    def _cancel_run(self) -> None:
        self._timer.stop()
        self._pending = None
        self._pool.cancel()
        self._set_running(False)
        self._status.setText(S.BACKTEST_CANCELLED)
