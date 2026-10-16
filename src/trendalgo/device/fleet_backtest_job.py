"""Fleet backtest job: TA fleet pass 1 in a worker. Progress is mirrored to the profile folder."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from trendalgo.backtest.fleet_runner import FleetPreflightError, get_fleet_runner
from trendalgo.device.fleet_backtest_model import FleetBacktestError
from trendalgo.device.fleet_progress import FleetProgressReporter, write_snapshot

POLL_S = 0.35
DEVICE_MAX_PASSES = 1


def fleet_backtest_job(
    profile_root: Path,
    data_dir: Path,
    exchange_id: str,
    pair: str,
    stake_usd: float,
    *,
    _offline_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run fleet pass 1 and return top10 + summary. Raises FleetBacktestError on failure.

    ``_offline_payload`` is test-only: a picklable result dict written without calling the runner.
    """
    if _offline_payload is not None:
        return _run_offline(profile_root, _offline_payload)
    runner = get_fleet_runner(data_dir)
    reporter = FleetProgressReporter(profile_root, runner)
    try:
        reporter.start()
        try:
            runner.start(
                exchange_id,
                pair,
                stake_usd,
                max_passes=DEVICE_MAX_PASSES,
            )
        except FleetPreflightError as exc:
            raise FleetBacktestError(str(exc)) from exc
        snap: dict[str, Any] | None = None
        while True:
            snap = runner.snapshot()
            if snap is None:
                break
            status = str(snap.get("status") or "")
            if status in ("complete", "error"):
                break
            time.sleep(POLL_S)
        if snap and snap.get("status") == "error":
            raise FleetBacktestError(str(snap.get("error") or "Fleet backtest failed."))
        payload = runner.consume_completed()
        if payload is None:
            raise FleetBacktestError("Fleet finished without a result.")
        return _normalize_result(payload)
    finally:
        reporter.stop()


def _run_offline(profile_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    write_snapshot(
        profile_root,
        {
            "status": "running",
            "phase": "pass1",
            "completed": 1,
            "total_combinations": 2,
            "progress_pct": 50,
            "eta_seconds": 1,
            "messages": ["offline fleet test"],
            "current_test": "RSI @ 60",
        },
    )
    time.sleep(0.05)
    write_snapshot(
        profile_root,
        {
            "status": "complete",
            "phase": "complete",
            "completed": 2,
            "total_combinations": 2,
            "progress_pct": 100,
            "eta_seconds": 0,
            "messages": ["offline fleet test done"],
        },
    )
    return _normalize_result(payload)


def _normalize_result(payload: dict[str, Any]) -> dict[str, Any]:
    raw_summary = payload.get("summary")
    summary: dict[str, Any] = raw_summary if isinstance(raw_summary, dict) else {}
    top10 = payload.get("top10")
    if not isinstance(top10, list):
        top10 = summary.get("final_top10") or summary.get("top10_pass1") or []
    return {
        "job_id": payload.get("job_id"),
        "exchange_id": payload.get("exchange_id"),
        "pair": payload.get("pair"),
        "stake_usd": payload.get("stake_usd"),
        "top10": top10,
        "summary": summary,
        "buy_and_hold": payload.get("buy_and_hold") or summary.get("buy_and_hold"),
    }
