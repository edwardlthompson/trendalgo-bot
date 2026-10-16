"""Live scan + backtest progress feed for the desktop scanner (in-process, thread-safe).

One ``ScanProgress`` singleton tracks the current run (scan and/or backtest jobs)
and a bounded event log. The dashboard polls ``GET /api/v1/scanner/progress``.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any, Literal

Level = Literal["info", "success", "warn", "error"]

_MAX_EVENTS = 400
_MAX_RUNNING_ITEMS = 8


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _idle_state() -> dict[str, Any]:
    return {
        "run_id": 0,
        "active": False,
        "open_jobs": 0,
        "status": "idle",
        "label": "",
        "phase": "",
        "step_done": 0,
        "step_total": 0,
        "step_unit": "",
        "started_at": None,
        "finished_at": None,
        "updated_at": None,
        "elapsed_s": 0.0,
        "phase_elapsed_s": 0.0,
        "running_items": [],
        "counts": {},
        "errors": 0,
    }


def _skip_reason_suffix(reasons: object) -> str:
    """Render coin skip reasons, e.g. ' (no_intraday_ohlcv x2)'. Empty when there are none."""
    if not isinstance(reasons, dict) or not reasons:
        return ""
    return " (" + ", ".join(f"{name} x{count}" for name, count in sorted(reasons.items())) + ")"


def _fmt_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


class ScanProgress:
    """Current-run summary plus a bounded, sequence-numbered event log."""

    def __init__(self, max_events: int = _MAX_EVENTS) -> None:
        self._lock = threading.RLock()
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._seq = 0
        self._state = _idle_state()
        self._run_started: float | None = None
        self._phase_started: float | None = None
        self._bt_decile = 0  # last 10% milestone logged for the current backtest phase

    # -- run lifecycle -------------------------------------------------------

    def begin_job(self, label: str) -> None:
        """Open a job. The first open job starts a new run; later ones join it."""
        with self._lock:
            if self._state["open_jobs"] == 0:
                run_id = int(self._state["run_id"]) + 1
                self._state = _idle_state()
                self._state.update(
                    run_id=run_id,
                    active=True,
                    status="running",
                    label=label,
                    phase=label,
                    started_at=_now_iso(),
                )
                self._run_started = time.monotonic()
                self._append("info", "run", f"Run #{run_id} started: {label}")
            else:
                self._append("info", "run", f"Joined run #{self._state['run_id']}: {label}")
            self._state["open_jobs"] += 1
            self._touch()

    def end_job(self) -> None:
        """Close a job. The run finishes when the last open job closes."""
        with self._lock:
            if self._state["open_jobs"] <= 0:
                return
            self._state["open_jobs"] -= 1
            if self._state["open_jobs"] > 0:
                self._touch()
                return
            elapsed = time.monotonic() - (self._run_started or time.monotonic())
            errors = int(self._state["errors"])
            self._state.update(
                active=False,
                status="done",
                phase="Done",
                finished_at=_now_iso(),
                elapsed_s=round(elapsed, 1),
                running_items=[],
            )
            tone: Level = "success" if errors == 0 else "warn"
            self._append(
                tone,
                "run",
                f"Run #{self._state['run_id']} finished in {_fmt_elapsed(elapsed)} "
                f"with {errors} error(s)",
            )
            self._touch()

    # -- progress updates ----------------------------------------------------

    def phase(self, name: str, *, total: int | None = None, unit: str = "") -> None:
        """Start a named phase; ``total``/``unit`` drive the progress bar."""
        with self._lock:
            self._phase_started = time.monotonic()
            self._state.update(
                phase=name,
                step_done=0,
                step_total=int(total or 0),
                step_unit=unit,
                running_items=[],
            )
            self._touch()
        self._append("info", name, f"Phase: {name}" + (f" ({total} {unit})" if total else ""))

    def step(self, done: int, *, total: int | None = None) -> None:
        """Update the current phase counter (no event line)."""
        with self._lock:
            self._state["step_done"] = int(done)
            if total is not None:
                self._state["step_total"] = int(total)
            self._touch()

    def set_counts(self, **counts: Any) -> None:
        with self._lock:
            self._state["counts"].update(counts)
            self._touch()

    def set_running(self, items: list[tuple[str, float]], *, pending: int = 0) -> None:
        """Heartbeat: symbols in flight with seconds since submit (state only, no event)."""
        with self._lock:
            self._state["running_items"] = [
                {"label": label, "elapsed_s": round(secs, 1)}
                for label, secs in items[:_MAX_RUNNING_ITEMS]
            ]
            self._state["counts"]["in_flight"] = int(pending)
            self._touch()

    def log(self, message: str, *, level: Level = "info", phase: str | None = None) -> None:
        """Append an activity line; ``error`` increments the run's error count."""
        with self._lock:
            if level == "error":
                self._state["errors"] = int(self._state["errors"]) + 1
            self._append(level, phase or str(self._state["phase"]), message)
            self._touch()

    # -- read side -----------------------------------------------------------

    def snapshot(self, after: int = 0, limit: int = 300) -> dict[str, Any]:
        """Return the current state plus events with ``seq > after`` (oldest first)."""
        with self._lock:
            state = dict(self._state)
            state["counts"] = dict(self._state["counts"])
            state["running_items"] = [dict(item) for item in self._state["running_items"]]
            if state["active"] and self._run_started is not None:
                state["elapsed_s"] = round(time.monotonic() - self._run_started, 1)
            if state["active"] and self._phase_started is not None:
                state["phase_elapsed_s"] = round(time.monotonic() - self._phase_started, 1)
            events = [event for event in self._events if int(event["seq"]) > int(after)]
            events = events[-max(1, int(limit)) :]
            last_seq = self._seq
        return {
            "state": state,
            "events": events,
            "last_seq": last_seq,
            "server_time": _now_iso(),
        }

    def backtest_event(self, event: dict[str, Any]) -> None:
        """Map backtest runner events (``bt_*``) into phase, counters, and log lines."""
        kind = str(event.get("event", ""))
        if kind == "bt_run_start":
            coins = int(event.get("total", 0))
            indicators = int(event.get("indicators", 0))
            timeframes = list(event.get("timeframes") or [])
            # One backtest = one strategy (or B&H) on one timeframe of one coin.
            runs_total = coins * len(timeframes) * (indicators + 1)
            self._bt_decile = 0
            self.phase("Backtest · all strategies + B&H", total=runs_total, unit="backtests")
            self.log(
                f"Backtesting {coins} coins × {indicators} indicators × {len(timeframes)} timeframes "
                f"({', '.join(timeframes) or 'n/a'}) + B&H = {runs_total} backtests"
            )
        elif kind == "bt_count":
            done = int(event.get("done", 0))
            total = int(event.get("total", 0))
            self.step(done, total=total)
            self._log_backtest_milestone(done, total)
        elif kind in {"bt_coin_done", "bt_coin_failed"}:
            completed = int(event.get("completed", 0))
            total = int(event.get("total", 0))
            symbol = str(event.get("symbol", "?"))
            if kind == "bt_coin_done":
                skip_note = _skip_reason_suffix(event.get("skip_reasons"))
                self.log(
                    f"{symbol}: {event.get('rows', 0)} strategy rows, "
                    f"{event.get('skipped', 0)} skipped{skip_note} ({completed}/{total})"
                )
            else:
                reason = str(event.get("reason", "unknown"))
                self.log(f"{symbol} failed: {reason} ({completed}/{total})", level="warn")
        elif kind == "bt_heartbeat":
            running = [(str(sym), float(secs)) for sym, secs in event.get("running") or []]
            self.set_running(running, pending=int(event.get("pending_count", 0)))
        elif kind == "bt_run_complete":
            failed = int(event.get("failed", 0))
            self.log(
                f"Backtest sweep complete: {event.get('processed', 0)} coins, "
                f"{event.get('rows', 0)} rows, {failed} failed",
                level="warn" if failed else "success",
            )
        elif kind == "bt_indicator_unavailable":
            indicator = str(event.get("indicator", "?"))
            reason = str(event.get("reason", "unavailable"))
            self.log(f"{indicator} skipped: {reason}", level="warn")

    # -- internals -----------------------------------------------------------

    def _log_backtest_milestone(self, done: int, total: int) -> None:
        """Log once per 10% of backtests, with time left estimated from the pace so far."""
        if total <= 0 or done <= 0:
            return
        decile = min(10, done * 10 // total)
        with self._lock:
            if decile <= self._bt_decile:
                return
            self._bt_decile = decile
            started = self._phase_started or time.monotonic()
        if done >= total:
            tail = "done"
        else:
            pace = (time.monotonic() - started) / done
            tail = f"about {_fmt_elapsed(pace * (total - done))} left"
        self.log(f"Backtests {done}/{total} ({decile * 10}%) · {tail}")

    def _touch(self) -> None:
        self._state["updated_at"] = _now_iso()

    def _append(self, level: Level, phase: str, message: str) -> None:
        self._seq += 1
        event = {
            "seq": self._seq,
            "ts": _now_iso(),
            "level": level,
            "phase": phase,
            "message": message,
        }
        self._events.append(event)
        try:
            print(f"[SCAN] {message}", flush=True)
        except (UnicodeEncodeError, OSError, ValueError):
            pass  # console encoding or closed stream; the event log still keeps the line


_PROGRESS = ScanProgress()


def get_scan_progress() -> ScanProgress:
    return _PROGRESS
