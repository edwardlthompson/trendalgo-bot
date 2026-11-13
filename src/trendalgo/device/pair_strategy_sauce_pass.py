"""Sauce-only pass: load frames, cook Lab/helpers on existing catalog rows (no re-catalog)."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from trendalgo.backtest.heartbeat_tf import needs_1m_base, sort_timeframes
from trendalgo.backtest.ohlcv_resample import frames_from_base
from trendalgo.backtest.oracle_catalog_coincidence import coincidence_sauce_row
from trendalgo.backtest.ta_fleet import MIN_BARS_FLOOR
from trendalgo.device import strings as S
from trendalgo.device.pair_strategy_secret_sauce import (
    current_lab_sauce,
    lab_oracle_row,
    mine_and_eval_secret_sauce,
    pending_sauce_row,
    refine_sauce_from_peers,
    unavailable_lab_row,
    upsert_secret_sauce,
    upsert_secret_sauce_ta,
    validate_sauce_against_peers,
)
from trendalgo.device.scan_base_ohlcv import load_base_ohlcv_frame
from trendalgo.device.scanner_protective_tsl import stamp_rows_protective_tsl

ProgressFn = Callable[[dict[str, Any]], None]
RowsFn = Callable[[list[dict[str, Any]]], None]
SAUCE_STEPS = 4


def run_sauce_only_pass(
    *,
    symbol: str,
    pair: str,
    timeframes: tuple[str, ...],
    seed_rows: list[dict[str, Any]],
    stake: float,
    fee: Any,
    loader: Any,
    gecko_id: str | None = None,
    prefs_root: Path | None = None,
    on_progress: ProgressFn | None = None,
    on_rows: RowsFn | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Cook Secret Sauce on catalog rows without re-running pass2 / deepen."""
    del prefs_root  # timing ledger optional; sauce-only is short
    out = [dict(r) for r in seed_rows]
    load_symbol = pair.split("/", 1)[0].strip().upper() if "/" in pair else symbol
    load_symbol = (load_symbol or symbol).upper()
    ordered_tf = sort_timeframes(timeframes)
    total = SAUCE_STEPS
    done = 0
    frames_by_tf: dict[str, Any] = {}

    def emit(message: str, **extra: Any) -> None:
        if on_progress is not None:
            on_progress({"message": message, "done": done, "total": total, **extra})

    def publish() -> None:
        if on_rows is not None:
            on_rows(list(out))

    base_hint = "1m" if needs_1m_base(ordered_tf) else "1h"
    emit(f"Sauce-only: loading {load_symbol} {base_hint}…", phase="load")
    t0 = time.perf_counter()
    base_frame, base_tf, data_source, cache_age_s = load_base_ohlcv_frame(
        symbol=load_symbol,
        pair=pair,
        timeframes=ordered_tf,
        loader=loader,
        gecko_id=gecko_id,
    )
    load_s = time.perf_counter() - t0
    if base_frame is None or base_frame.empty:
        emit("Sauce-only: no OHLCV — keeping catalog rows", phase="done", done=total)
        return out, {
            "include_sauce": False,
            "sauce_only": True,
            "phase_s": {"load_s": round(load_s, 3), "sauce_s": 0.0},
            "data_source": data_source,
            "cache_age_s": cache_age_s,
        }

    resampled = frames_from_base(base_frame, ordered_tf)
    for timeframe in ordered_tf:
        frame = resampled.get(timeframe)
        if frame is None or frame.empty or len(frame) < MIN_BARS_FLOOR:
            continue
        frames_by_tf[timeframe] = frame

    lab_oracle = lab_oracle_row(out)
    ss_future = None
    ss_pool = None
    t_ss_start = time.perf_counter()
    if lab_oracle is not None:
        ss_tf = str(lab_oracle.get("timeframe") or "1h")
        out.append(pending_sauce_row(symbol=symbol, timeframe=ss_tf, stake=stake))
        publish()
        emit(f"Secret Sauce Lab started on {ss_tf}…", phase="sauce", ss_lab_pending=True)
        ss_pool = ThreadPoolExecutor(max_workers=1)
        ss_future = ss_pool.submit(
            mine_and_eval_secret_sauce,
            lab_oracle,
            frames_by_tf=frames_by_tf,
            symbol=symbol,
            stake=stake,
            fee=fee,
        )

    t_sauce = time.perf_counter()
    emit(S.SCAN_PHASE_SAUCE_COINCIDENCE, phase="sauce", catalog_ready=True)
    if lab_oracle is not None:
        o_tf = str(lab_oracle.get("timeframe") or "1h")
        o_frame = frames_by_tf.get(o_tf)
        if o_frame is not None:
            try:
                coin = coincidence_sauce_row(
                    o_frame, lab_oracle, out, fee=fee, stake=stake, symbol=symbol
                )
            except (TypeError, ValueError, KeyError, IndexError):
                coin = None
            if coin is not None:
                out = upsert_secret_sauce_ta(out, coin)
                publish()
                emit(f"Secret Sauce TA recorded ({coin.get('net_pct')}%)", phase="sauce")
    done = 1
    emit(S.SCAN_PHASE_SAUCE_COINCIDENCE + " done", phase="sauce", ss_ta_done=True)

    sauce: dict[str, Any] | None = None
    if ss_future is not None:
        try:
            sauce = ss_future.result()
        except Exception as exc:
            sauce = None
            emit(f"Secret Sauce Lab mine failed: {exc}", phase="sauce")
        emit(
            f"{S.SCAN_PHASE_SAUCE_MERGE} total={time.perf_counter() - t_ss_start:.2f}s",
            phase="sauce",
        )
    if ss_pool is not None:
        ss_pool.shutdown(wait=False)

    base = sauce if sauce is not None else current_lab_sauce(out)
    if base is not None:
        emit(S.SCAN_PHASE_SAUCE_REFINE, phase="sauce")
        try:
            base = refine_sauce_from_peers(base, out, frames_by_tf, stake=stake, fee=fee)
        except (TypeError, ValueError, KeyError, IndexError):
            pass
        ok, reason = validate_sauce_against_peers(base, out, frames_by_tf, stake=stake, fee=fee)
        base = dict(base)
        base["ss_lab_pending"] = False
        base["ss_unavailable"] = False
        base["spectrum_ok"] = bool(ok)
        if not ok:
            base["spectrum_note"] = reason
        out = upsert_secret_sauce(out, base)
        publish()
        emit(
            "Secret Sauce Lab recorded" if ok else f"Secret Sauce Lab recorded ({reason})",
            phase="sauce",
        )
    else:
        ss_tf = str((lab_oracle or {}).get("timeframe") or "1h") if lab_oracle else "1h"
        note = "no fee-honest Lab recipe on this window"
        out = upsert_secret_sauce(
            out, unavailable_lab_row(symbol=symbol, timeframe=ss_tf, stake=stake, reason=note)
        )
        publish()
        emit(f"Secret Sauce Lab unavailable — {note}", phase="sauce")
    done = 2
    emit("Secret Sauce helpers cooking…", phase="sauce", ss_helpers=True)

    if lab_oracle is not None:
        from trendalgo.backtest.secret_sauce_lab.sauce_cook import cook_sauce_suite
        from trendalgo.device.pair_strategy_secret_sauce import upsert_sauce_named
        from trendalgo.device.sauce_names import is_sauce_ta

        sauce_ta_row = next((r for r in out if is_sauce_ta(r.get("indicator"))), None)
        core = current_lab_sauce(out)

        def _helper_emit(msg: str) -> None:
            emit(msg, phase="sauce")

        try:
            helper_rows = cook_sauce_suite(
                oracle=lab_oracle,
                rows=out,
                frames_by_tf=frames_by_tf,
                symbol=symbol,
                stake=stake,
                fee=fee,
                core_lab=core,
                sauce_ta=sauce_ta_row,
                emit=_helper_emit,
            )
        except Exception as exc:
            helper_rows = []
            emit(f"Secret Sauce helpers soft-fail: {exc}", phase="sauce")
        for hr in helper_rows:
            name = str(hr.get("indicator") or "")
            if name.startswith("_sauce_"):
                continue
            out = upsert_sauce_named(out, hr, name=name)
            publish()
    done = 3
    emit("Secret Sauce Final / helpers done", phase="sauce", ss_final_done=True)

    out = stamp_rows_protective_tsl(out, frames_by_tf, fee=fee, stake=stake)
    publish()
    sauce_s = time.perf_counter() - t_sauce
    done = total
    ctx = {
        "include_sauce": True,
        "sauce_only": True,
        "data_source": data_source,
        "cache_age_s": cache_age_s,
        "phase_s": {"load_s": round(load_s, 3), "sauce_s": round(sauce_s, 3)},
    }
    emit(f"Sauce-only complete — {len(out)} rows", phase="done", done=total)
    publish()
    return out, ctx
