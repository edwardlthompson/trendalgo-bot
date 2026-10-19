"""Parallel All-TA Pass 2 (catalog signal-only) for Backtest pair scan."""

from __future__ import annotations

import multiprocessing
import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

from trendalgo.backtest.fleet_config import PASS12_TRAILING_STOP_PCT
from trendalgo.backtest.ta_fleet import backtest_one

ProgressFn = Callable[[dict[str, Any]], None]
SIGNAL_TSL = float(PASS12_TRAILING_STOP_PCT)

# Process-pool worker state (initializer; one frame per TF batch).
_W_FRAME: pd.DataFrame | None = None
_W_FEE: Any = None
_W_STAKE: float = 0.0
_W_TF: str = "1h"
_W_TSL: float = SIGNAL_TSL


def _init_worker(frame: pd.DataFrame, fee: Any, stake: float, tf: str, tsl: float) -> None:
    global _W_FRAME, _W_FEE, _W_STAKE, _W_TF, _W_TSL
    _W_FRAME = frame
    _W_FEE = fee
    _W_STAKE = stake
    _W_TF = tf
    _W_TSL = tsl


def _bt_sid(sid: str) -> tuple[str, dict[str, Any] | None, str | None]:
    assert _W_FRAME is not None
    row, reason = backtest_one(
        _W_FRAME,
        sid,
        _W_FEE,
        _W_STAKE,
        timeframe=_W_TF,
        lookback_seconds=0,
        trailing_stop_pct=_W_TSL,
    )
    return sid, row, reason


def pass2_worker_count() -> int:
    return max(1, min(8, int(os.cpu_count() or 4)))


def run_catalog_pass2(
    *,
    frames_by_tf: dict[str, pd.DataFrame],
    ordered_tf: tuple[str, ...] | list[str],
    strat_list: tuple[str, ...],
    fee: Any,
    stake: float,
    done_start: int,
    total: int,
    on_progress: ProgressFn | None = None,
    on_tf_rows: Callable[[str, list[dict[str, Any]]], None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str], int]:
    """Run signal-only catalog for each TF. Returns (signal_rows, skip_best, done)."""
    signal_rows: list[dict[str, Any]] = []
    skip_best: dict[str, str] = {}
    done = done_start
    workers = pass2_worker_count()

    def emit(message: str, **extra: Any) -> None:
        if on_progress is not None:
            on_progress({"message": message, "done": done, "total": total, **extra})

    for timeframe in ordered_tf:
        frame = frames_by_tf.get(timeframe)
        if frame is None:
            done += len(strat_list)
            continue
        from trendalgo.device import strings as S

        emit(
            f"{S.SCAN_PHASE_CATALOG} {timeframe} ×{len(strat_list)} (workers={workers})",
            phase="catalog",
            timeframe=timeframe,
        )
        results = _map_strategies(frame, timeframe, strat_list, fee, stake, workers)
        tf_hits: list[dict[str, Any]] = []
        for index, (sid, row, reason) in enumerate(results, start=1):
            done += 1
            if index == 1 or index == len(strat_list) or index % 32 == 0:
                emit(
                    f"{timeframe} {sid} ({index}/{len(strat_list)})",
                    phase="catalog",
                    timeframe=timeframe,
                    strategy=sid,
                )
            if row is None:
                skip_best.setdefault(sid, reason or "compute_error")
                continue
            signal_rows.append(row)
            tf_hits.append(row)
        if on_tf_rows is not None and tf_hits:
            on_tf_rows(timeframe, tf_hits)
        emit(
            f"{timeframe} catalog done — {len(signal_rows)} signal rows",
            phase="tf_done",
            timeframe=timeframe,
        )
    return signal_rows, skip_best, done


def _map_strategies(
    frame: pd.DataFrame,
    timeframe: str,
    strat_list: tuple[str, ...],
    fee: Any,
    stake: float,
    workers: int,
) -> list[tuple[str, dict[str, Any] | None, str | None]]:
    if workers <= 1 or len(strat_list) < 4:
        return [_bt_one_local(frame, timeframe, sid, fee, stake) for sid in strat_list]
    # Device WorkerPool uses daemon processes; nested ProcessPool raises AssertionError.
    if multiprocessing.current_process().daemon:
        return _map_threads(frame, timeframe, strat_list, fee, stake, workers)
    try:
        return _map_process(frame, timeframe, strat_list, fee, stake, workers)
    except (OSError, PermissionError, ValueError, RuntimeError, AssertionError):
        return _map_threads(frame, timeframe, strat_list, fee, stake, workers)


def _bt_one_local(
    frame: pd.DataFrame, timeframe: str, sid: str, fee: Any, stake: float
) -> tuple[str, dict[str, Any] | None, str | None]:
    row, reason = backtest_one(
        frame,
        sid,
        fee,
        stake,
        timeframe=timeframe,
        lookback_seconds=0,
        trailing_stop_pct=SIGNAL_TSL,
    )
    return sid, row, reason


def _map_process(
    frame: pd.DataFrame,
    timeframe: str,
    strat_list: tuple[str, ...],
    fee: Any,
    stake: float,
    workers: int,
) -> list[tuple[str, dict[str, Any] | None, str | None]]:
    out: dict[str, tuple[str, dict[str, Any] | None, str | None]] = {}
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_worker,
        initargs=(frame, fee, stake, timeframe, SIGNAL_TSL),
    ) as pool:
        futs = {pool.submit(_bt_sid, sid): sid for sid in strat_list}
        for fut in as_completed(futs):
            sid, row, reason = fut.result()
            out[sid] = (sid, row, reason)
    return [out[sid] for sid in strat_list]


def _map_threads(
    frame: pd.DataFrame,
    timeframe: str,
    strat_list: tuple[str, ...],
    fee: Any,
    stake: float,
    workers: int,
) -> list[tuple[str, dict[str, Any] | None, str | None]]:
    out: dict[str, tuple[str, dict[str, Any] | None, str | None]] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(_bt_one_local, frame, timeframe, sid, fee, stake): sid for sid in strat_list
        }
        for fut in as_completed(futs):
            sid, row, reason = fut.result()
            out[sid] = (sid, row, reason)
    return [out[sid] for sid in strat_list]
