"""Shared ApplicationModal scan progress — bar, pair glance, ETA, activity log."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Sequence
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.backtest_notify import format_elapsed_s
from trendalgo.device.backtest_scan_eta import (
    append_log_line,
    format_pace,
    format_remaining,
    remaining_seconds,
)
from trendalgo.device.backtest_scan_eta import (
    progress_pct as eta_progress_pct,
)


def format_pair_label(raw: str | None) -> str:
    """Display pair; promote bare symbols to BASE/USD."""
    text = str(raw or "").strip()
    if not text or text in {"?", "—", "-"}:
        return "—"
    if "/" in text:
        return text.upper()
    return f"{text.upper()}/USD"


def format_pairs_remaining(*, done: int | None, total: int | None) -> str:
    if total is None or int(total) <= 0:
        return S.SCAN_PROGRESS_PAIRS_UNKNOWN
    done_n = max(0, int(done or 0))
    total_n = max(0, int(total))
    remaining = max(0, total_n - done_n)
    return S.SCAN_PROGRESS_PAIRS_REMAINING.format(remaining=remaining, done=done_n, total=total_n)


def glance_from_progress(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize Scanner or Backtest progress payloads into dialog glance fields."""
    if not isinstance(raw, dict):
        return {
            "done": 0,
            "total": 0,
            "unit": "",
            "message": "",
            "current_pair": "—",
            "pairs_done": None,
            "pairs_total": None,
        }
    state = raw.get("state") if isinstance(raw.get("state"), dict) else {}
    done = _int(raw.get("done"), _int(state.get("step_done"), 0))
    total = _int(raw.get("total"), _int(state.get("step_total"), 0))
    unit = str(raw.get("unit") or state.get("step_unit") or "").strip()
    message = str(raw.get("message") or "").strip()
    if not message and state.get("phase"):
        message = str(state.get("phase"))
    current = raw.get("current_pair")
    if current is None:
        current = state.get("current_pair")
    pairs_done = raw.get("pairs_done")
    if pairs_done is None:
        pairs_done = state.get("pairs_done")
    pairs_total = raw.get("pairs_total")
    if pairs_total is None:
        pairs_total = state.get("pairs_total")
    try:
        pairs_done_i = int(pairs_done) if pairs_done is not None else None
    except (TypeError, ValueError):
        pairs_done_i = None
    try:
        pairs_total_i = int(pairs_total) if pairs_total is not None else None
    except (TypeError, ValueError):
        pairs_total_i = None
    return {
        "done": done,
        "total": total,
        "unit": unit,
        "message": message,
        "current_pair": format_pair_label(str(current) if current is not None else None),
        "pairs_done": pairs_done_i,
        "pairs_total": pairs_total_i,
    }


def _int(raw: object, default: int = 0) -> int:
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


class ScanProgressDialog(QDialog):
    """Blocking verbose progress shared by Backtest and Opportunity Scanner."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        seed_lines: Sequence[str],
        on_cancel: Callable[[], None],
        prior_s: float = 0.0,
        initial_total: int = 1,
        initial_pair: str = "—",
        initial_pairs_total: int | None = None,
        count_label: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_cancel = on_cancel
        self._prior_s = max(0.0, float(prior_s))
        self._total = max(1, int(initial_total))
        self._t0 = time.perf_counter()
        self._log_lines: list[str] = []
        self._last_message = ""
        self._allow_close = False
        self._count_template = count_label or S.SCAN_PROGRESS_STEPS

        self.setWindowTitle(title)
        self.setMinimumSize(420, 400)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        self._steps = QLabel(self._count_template.format(done=0, total=self._total, unit=""))
        self._current_pair = QLabel(
            S.SCAN_PROGRESS_CURRENT_PAIR.format(pair=format_pair_label(initial_pair))
        )
        self._pairs_left = QLabel(format_pairs_remaining(done=0, total=initial_pairs_total))
        self._elapsed = QLabel(S.SCAN_PROGRESS_ELAPSED.format(elapsed="0s"))
        self._eta = QLabel(S.SCAN_PROGRESS_ETA.format(remaining="—"))
        self._pace = QLabel("")
        self._pace.setObjectName("hint")
        for lbl in (
            self._steps,
            self._current_pair,
            self._pairs_left,
            self._elapsed,
            self._eta,
            self._pace,
        ):
            lbl.setWordWrap(True)

        self._phase = QLabel(S.SCAN_PROGRESS_STARTING)
        self._phase.setWordWrap(True)
        phase_cap = QLabel(S.SCAN_PROGRESS_PHASE)
        phase_cap.setObjectName("sectionTitle")
        log_cap = QLabel(S.SCAN_PROGRESS_LOG)
        log_cap.setObjectName("sectionTitle")
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(140)

        self._cancel = QPushButton(S.SCAN_PROGRESS_CANCEL)
        self._cancel.clicked.connect(self._handle_cancel)
        hint = QLabel(S.SCAN_PROGRESS_HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        metrics = QHBoxLayout()
        metrics.addWidget(self._elapsed)
        metrics.addWidget(self._eta)
        metrics.addWidget(self._pace)
        metrics.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._bar)
        layout.addWidget(self._steps)
        layout.addWidget(self._current_pair)
        layout.addWidget(self._pairs_left)
        layout.addLayout(metrics)
        layout.addWidget(phase_cap)
        layout.addWidget(self._phase)
        layout.addWidget(log_cap)
        layout.addWidget(self._log, 1)
        layout.addWidget(hint)
        layout.addWidget(self._cancel)

        for line in seed_lines:
            self._append(str(line))
        if not seed_lines:
            self._append(S.SCAN_PROGRESS_STARTING)

        self._tick = QTimer(self)
        self._tick.setInterval(250)
        self._tick.timeout.connect(self._refresh_elapsed)
        self._tick.start()
        self._cancel.setFocus(Qt.FocusReason.OtherFocusReason)

    def update_progress(
        self,
        raw: dict[str, Any] | None,
        *,
        worker_ready: bool = False,
        extra_log_lines: Sequence[str] = (),
        append_phase_to_log: bool = True,
    ) -> None:
        glance = glance_from_progress(raw)
        done = int(glance["done"])
        total = max(1, int(glance["total"] or self._total))
        self._total = total
        unit = str(glance["unit"] or "")
        unit_bit = f" {unit}" if unit else ""
        self._steps.setText(self._count_template.format(done=done, total=total, unit=unit_bit))
        self._current_pair.setText(S.SCAN_PROGRESS_CURRENT_PAIR.format(pair=glance["current_pair"]))
        self._pairs_left.setText(
            format_pairs_remaining(done=glance["pairs_done"], total=glance["pairs_total"])
        )
        self._bar.setValue(eta_progress_pct(done=done, total=total, worker_ready=worker_ready))
        message = str(glance["message"] or "")
        if message and message != self._last_message:
            self._last_message = message
            self._phase.setText(message)
            if append_phase_to_log:
                self._append(message)
        for line in extra_log_lines:
            self._append(line)
        elapsed = time.perf_counter() - self._t0
        self._elapsed.setText(S.SCAN_PROGRESS_ELAPSED.format(elapsed=format_elapsed_s(elapsed)))
        stamped = None
        if isinstance(raw, dict) and raw.get("eta_remaining_s") is not None:
            try:
                stamped = float(raw["eta_remaining_s"])
            except (TypeError, ValueError):
                stamped = None
        snap = remaining_seconds(
            elapsed_s=elapsed,
            done=done,
            total=total,
            prior_s=self._prior_s,
            stamped_remaining_s=stamped,
        )
        self._eta.setText(S.SCAN_PROGRESS_ETA.format(remaining=format_remaining(snap.remaining_s)))
        pace = format_pace(snap.pace_s)
        self._pace.setText(S.SCAN_PROGRESS_PACE.format(pace=pace) if pace else "")

    def finish_and_close(self) -> None:
        self._allow_close = True
        self._tick.stop()
        self.accept()

    def reject_cancel_close(self) -> None:
        self._allow_close = True
        self._tick.stop()
        self.reject()

    def nudge_blocked(self) -> None:
        _system_bong()
        try:
            QApplication.alert(self, 1500)
        except Exception:
            pass
        self._flash_border()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        self.nudge_blocked()

    def reject(self) -> None:  # noqa: A003
        if self._allow_close:
            super().reject()
            return
        self.nudge_blocked()

    def keyPressEvent(self, event: Any) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.nudge_blocked()
            event.ignore()
            return
        super().keyPressEvent(event)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def _handle_cancel(self) -> None:
        self._on_cancel()

    def _refresh_elapsed(self) -> None:
        elapsed = time.perf_counter() - self._t0
        self._elapsed.setText(S.SCAN_PROGRESS_ELAPSED.format(elapsed=format_elapsed_s(elapsed)))

    def _append(self, message: str) -> None:
        self._log_lines = append_log_line(self._log_lines, message)
        self._log.setPlainText("\n".join(self._log_lines))
        cursor = self._log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._log.setTextCursor(cursor)

    def _flash_border(self) -> None:
        prev = self.styleSheet()
        self.setStyleSheet(
            "QDialog { border: 2px solid palette(highlight); }" + ((" " + prev) if prev else "")
        )

        def _clear() -> None:
            self.setStyleSheet(prev)

        QTimer.singleShot(400, _clear)


def _system_bong() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBeep(0)
            return
        except Exception:
            pass
    try:
        QApplication.beep()
    except Exception:
        pass


def apply_main_blur(window: QWidget | None, *, enabled: bool) -> None:
    """Blur the main window central widget while the scan modal is open."""
    if window is None:
        return
    target = window
    central = getattr(window, "centralWidget", None)
    if callable(central):
        widget = central()
        if isinstance(widget, QWidget):
            target = widget
    try:
        from PySide6.QtWidgets import QGraphicsBlurEffect

        if enabled:
            effect = QGraphicsBlurEffect(target)
            effect.setBlurRadius(8.0)
            target.setGraphicsEffect(effect)
        else:
            target.setGraphicsEffect(None)
    except Exception:
        pass
