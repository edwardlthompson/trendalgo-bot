"""Parallel All-TA Pass 2 (catalog signal-only) for Backtest pair scan."""

from __future__ import annotations

import multiprocessing
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

from trendalgo.backtest.fleet_config import PASS12_TRAILING_STOP_PCT
from trendalgo.backtest.ta_fleet import backtest_one
from trendalgo.device.scan_parallel import pass2_worker_count
from trendalgo.device.scan_unit_timing import UnitSample, top_slowest

ProgressFn = Callable[[dict[str, Any]], None]
UnitTimingsFn = Callable[[list[UnitSample]], None]
BtResult = tuple[str, dict[str, Any] | None, str | None, float]
SIGNAL_TSL = float(PASS12_TRAILING_STOP_PCT)

# Re-export for callers that imported pass2_worker_count from this module.
__all__ = ["pass2_worker_count", "run_catalog_pass2"]

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


def _bt_sid(sid: str) -> BtResult:
    assert _W_FRAME is not None
    t0 = time.perf_counter()
    row, reason = backtest_one(
        _W_FRAME,
        sid,
        _W_FEE,
        _W_STAKE,
        timeframe=_W_TF,
        lookback_seconds=0,
        trailing_stop_pct=_W_TSL,
    )
    return sid, row, reason, time.perf_counter() - t0


def run_catalog_pass2(
    *,
    frames_by_tf: dict[str, pd.DataFrame],
    ordered_tf: tuple[str, ...] | list[str],
    strat_list: tuple[str, ...],
    fee: Any,
    stake: float,
    done_start: int,
    total: int,
    pair: str = "",
    on_progress: ProgressFn | None = None,
    on_tf_rows: Callable[[str, list[dict[str, Any]]], None] | None = None,
    on_unit_timings: UnitTimingsFn | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str], int, list[UnitSample]]:
    """Run signal-only catalog for each TF. Returns rows, skips, done, unit timings."""
    signal_rows: list[dict[str, Any]] = []
    skip_best: dict[str, str] = {}
    all_units: list[UnitSample] = []
    done = done_start
    workers = pass2_worker_count()
    pair_text = str(pair or "").strip()

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
        tf_units: list[UnitSample] = []
        for index, (sid, row, reason, elapsed_s) in enumerate(results, start=1):
            done += 1
            sample = UnitSample(
                strategy=sid,
                timeframe=timeframe,
                pair=pair_text,
                elapsed_s=float(elapsed_s),
                phase="catalog",
            )
            tf_units.append(sample)
            all_units.append(sample)
            if index == 1 or index == len(strat_list) or index % 32 == 0:
                emit(
                    f"{timeframe} {sid} ({index}/{len(strat_list)})",
                    phase="catalog",
                    timeframe=timeframe,
                    strategy=sid,
                    unit_elapsed_s=round(float(elapsed_s), 3),
                )
            if row is None:
                skip_best.setdefault(sid, reason or "compute_error")
                continue
            signal_rows.append(row)
            tf_hits.append(row)
        if on_tf_rows is not None and tf_hits:
            on_tf_rows(timeframe, tf_hits)
        slow = top_slowest(tf_units, 3)
        if slow:
            bits = ", ".join(f"{u.strategy}@{u.timeframe} {u.elapsed_s:.2f}s" for u in slow)
            emit(f"Slow: {bits}", phase="tf_done", timeframe=timeframe)
        if on_unit_timings is not None and tf_units:
            on_unit_timings(tf_units)
        emit(
            f"{timeframe} catalog done — {len(signal_rows)} signal rows",
            phase="tf_done",
            timeframe=timeframe,
        )
    return signal_rows, skip_best, done, all_units


def _map_strategies(
    frame: pd.DataFrame,
    timeframe: str,
    strat_list: tuple[str, ...],
    fee: Any,
    stake: float,
    workers: int,
) -> list[BtResult]:
    if workers <= 1 or len(strat_list) < 4:
        return [_bt_one_local(frame, timeframe, sid, fee, stake) for sid in strat_list]
    if multiprocessing.current_process().daemon:
        return _map_threads(frame, timeframe, strat_list, fee, stake, workers)
    try:
        return _map_process(frame, timeframe, strat_list, fee, stake, workers)
    except (OSError, PermissionError, ValueError, RuntimeError, AssertionError):
        return _map_threads(frame, timeframe, strat_list, fee, stake, workers)


def _bt_one_local(
    frame: pd.DataFrame, timeframe: str, sid: str, fee: Any, stake: float
) -> BtResult:
    t0 = time.perf_counter()
    row, reason = backtest_one(
        frame,
        sid,
        fee,
        stake,
        timeframe=timeframe,
        lookback_seconds=0,
        trailing_stop_pct=SIGNAL_TSL,
    )
    return sid, row, reason, time.perf_counter() - t0


def _map_process(
    frame: pd.DataFrame,
    timeframe: str,
    strat_list: tuple[str, ...],
    fee: Any,
    stake: float,
    workers: int,
) -> list[BtResult]:
    out: dict[str, BtResult] = {}
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_worker,
        initargs=(frame, fee, stake, timeframe, SIGNAL_TSL),
    ) as pool:
        futs = {pool.submit(_bt_sid, sid): sid for sid in strat_list}
        for fut in as_completed(futs):
            sid, row, reason, elapsed = fut.result()
            out[sid] = (sid, row, reason, elapsed)
    return [out[sid] for sid in strat_list]


def _map_threads(
    frame: pd.DataFrame,
    timeframe: str,
    strat_list: tuple[str, ...],
    fee: Any,
    stake: float,
    workers: int,
) -> list[BtResult]:
    out: dict[str, BtResult] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(_bt_one_local, frame, timeframe, sid, fee, stake): sid for sid in strat_list
        }
        for fut in as_completed(futs):
            sid, row, reason, elapsed = fut.result()
            out[sid] = (sid, row, reason, elapsed)
    return [out[sid] for sid in strat_list]
