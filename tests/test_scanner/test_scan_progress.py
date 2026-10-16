"""Scan + backtest progress feed (run lifecycle, counters, bounded event log)."""

from __future__ import annotations

import pytest

import trendalgo.scanner.progress as progress_module
from trendalgo.scanner.progress import ScanProgress


def test_phase_elapsed_restarts_with_each_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"now": 100.0}
    monkeypatch.setattr(progress_module.time, "monotonic", lambda: clock["now"])
    progress = ScanProgress()
    assert progress.snapshot()["state"]["phase_elapsed_s"] == 0.0

    progress.begin_job("Scan")
    progress.phase("Universe", total=3, unit="pairs")
    clock["now"] = 112.5
    assert progress.snapshot()["state"]["phase_elapsed_s"] == 12.5

    progress.phase("Qualify", total=2, unit="pairs")
    clock["now"] = 115.0
    state = progress.snapshot()["state"]
    assert state["phase_elapsed_s"] == 2.5
    assert state["elapsed_s"] == 15.0
    progress.end_job()


def test_joined_jobs_keep_one_run_active_until_last_job_ends() -> None:
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.begin_job("Backtest")
    assert progress.snapshot()["state"]["run_id"] == 1

    progress.end_job()
    assert progress.snapshot()["state"]["active"] is True

    progress.end_job()
    state = progress.snapshot()["state"]
    assert state["active"] is False
    assert state["status"] == "done"
    assert state["finished_at"]


def test_backtest_events_drive_counters_heartbeat_and_log() -> None:
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.backtest_event(
        {"event": "bt_run_start", "total": 3, "indicators": 12, "timeframes": ["1h", "4h"]}
    )
    progress.backtest_event(
        {"event": "bt_heartbeat", "pending_count": 2, "running": [("NEAR", 4.2), ("US", 1.0)]}
    )
    progress.backtest_event({"event": "bt_count", "done": 13, "total": 78})
    progress.backtest_event(
        {
            "event": "bt_coin_done",
            "symbol": "NEAR",
            "completed": 1,
            "total": 3,
            "rows": 10,
            "skipped": 16,
        }
    )
    snap = progress.snapshot()
    state = snap["state"]
    assert state["phase"].startswith("Backtest")
    # The bar counts backtests; a finished coin logs a line but does not move it.
    assert (state["step_unit"], state["step_done"], state["step_total"]) == ("backtests", 13, 78)
    assert [item["label"] for item in state["running_items"]] == ["NEAR", "US"]
    assert state["counts"]["in_flight"] == 2
    assert any("NEAR: 10 strategy rows" in event["message"] for event in snap["events"])
    progress.end_job()


def test_run_start_plans_every_backtest_coin_by_timeframe_by_strategy() -> None:
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.backtest_event(
        {"event": "bt_run_start", "total": 3, "indicators": 12, "timeframes": ["1h", "4h"]}
    )
    state = progress.snapshot()["state"]
    # 3 coins x 2 timeframes x (12 indicators + B&H) = 78 backtests
    assert (state["step_done"], state["step_total"], state["step_unit"]) == (0, 78, "backtests")
    messages = [event["message"] for event in progress.snapshot()["events"]]
    assert any(message.endswith("= 78 backtests") for message in messages)
    progress.end_job()


def test_backtest_count_logs_each_tenth_once_with_time_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = {"now": 100.0}
    monkeypatch.setattr(progress_module.time, "monotonic", lambda: clock["now"])
    progress = ScanProgress()
    progress.begin_job("Scan")
    # 10 coins x 1 timeframe x (7 indicators + B&H) = 80 backtests
    progress.backtest_event(
        {"event": "bt_run_start", "total": 10, "indicators": 7, "timeframes": ["1h"]}
    )

    clock["now"] = 110.0  # 8 done in 10 s -> 1.25 s each, 72 left -> 01:30
    progress.backtest_event({"event": "bt_count", "done": 8, "total": 80})
    clock["now"] = 111.0  # still inside the same tenth: no new line
    progress.backtest_event({"event": "bt_count", "done": 9, "total": 80})
    clock["now"] = 120.0  # 16 done in 20 s -> 1.25 s each, 64 left -> 01:20
    progress.backtest_event({"event": "bt_count", "done": 16, "total": 80})
    progress.backtest_event({"event": "bt_count", "done": 80, "total": 80})

    messages = [
        event["message"]
        for event in progress.snapshot()["events"]
        if event["message"].startswith("Backtests ")
    ]
    assert messages == [
        "Backtests 8/80 (10%) · about 01:30 left",
        "Backtests 16/80 (20%) · about 01:20 left",
        "Backtests 80/80 (100%) · done",
    ]
    state = progress.snapshot()["state"]
    assert (state["step_done"], state["step_total"]) == (80, 80)
    progress.end_job()


def test_backtest_count_without_planned_work_logs_nothing() -> None:
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.backtest_event({"event": "bt_count", "done": 0, "total": 0})
    progress.backtest_event({"event": "bt_count", "done": 0, "total": 12})
    assert not [
        event
        for event in progress.snapshot()["events"]
        if event["message"].startswith("Backtests ")
    ]
    progress.end_job()


def test_skipped_coin_line_says_why_its_rows_are_missing() -> None:
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.backtest_event(
        {
            "event": "bt_coin_done",
            "symbol": "XYZ",
            "completed": 1,
            "total": 2,
            "rows": 0,
            "skipped": 2,
            "skip_reasons": {"no_intraday_ohlcv": 2},
        }
    )
    messages = [event["message"] for event in progress.snapshot()["events"]]
    assert any(
        "XYZ: 0 strategy rows, 2 skipped (no_intraday_ohlcv x2) (1/2)" in message
        for message in messages
    )
    progress.end_job()


def test_failed_coin_and_failed_sweep_are_logged_as_warnings() -> None:
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.backtest_event(
        {
            "event": "bt_coin_failed",
            "symbol": "ZRO",
            "completed": 1,
            "total": 2,
            "reason": "no_intraday_ohlcv",
        }
    )
    last = progress.snapshot()["events"][-1]
    assert last["level"] == "warn"
    assert last["message"] == "ZRO failed: no_intraday_ohlcv (1/2)"

    progress.backtest_event({"event": "bt_run_complete", "processed": 2, "rows": 7, "failed": 1})
    last = progress.snapshot()["events"][-1]
    assert last["level"] == "warn"
    assert last["message"] == "Backtest sweep complete: 2 coins, 7 rows, 1 failed"
    progress.end_job()


def test_console_encoding_failure_still_keeps_the_event(monkeypatch: pytest.MonkeyPatch) -> None:
    def _unprintable(*_args: object, **_kwargs: object) -> None:
        raise UnicodeEncodeError("cp1252", "", 0, 1, "unencodable")

    monkeypatch.setattr("builtins.print", _unprintable)
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.log("Kraken → ok")
    assert progress.snapshot()["events"][-1]["message"] == "Kraken → ok"
    progress.end_job()


def test_unavailable_indicator_is_logged_as_warning() -> None:
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.backtest_event(
        {
            "event": "bt_indicator_unavailable",
            "indicator": "Stochastic",
            "reason": "TA-Lib required for stochastic_signals",
        }
    )
    last = progress.snapshot()["events"][-1]
    assert last["level"] == "warn"
    assert last["message"] == "Stochastic skipped: TA-Lib required for stochastic_signals"
    progress.end_job()


def test_snapshot_after_returns_only_newer_events() -> None:
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.log("first")
    cursor = progress.snapshot()["last_seq"]
    progress.log("second")
    newer = progress.snapshot(after=cursor)["events"]
    assert [event["message"] for event in newer] == ["second"]
    progress.end_job()


def test_event_log_is_bounded() -> None:
    progress = ScanProgress(max_events=5)
    progress.begin_job("Scan")
    for index in range(20):
        progress.log(f"line {index}")
    events = progress.snapshot(limit=300)["events"]
    assert len(events) == 5
    assert events[-1]["message"] == "line 19"
    progress.end_job()


def test_error_lines_count_toward_run_errors() -> None:
    progress = ScanProgress()
    progress.begin_job("Scan")
    progress.log("live market fetch failed", level="error")
    progress.log("1 pair skipped", level="warn")
    progress.end_job()
    state = progress.snapshot()["state"]
    assert state["errors"] == 1
    assert state["status"] == "done"


def test_end_job_without_begin_is_a_no_op() -> None:
    progress = ScanProgress()
    progress.end_job()
    assert progress.snapshot()["state"]["status"] == "idle"
