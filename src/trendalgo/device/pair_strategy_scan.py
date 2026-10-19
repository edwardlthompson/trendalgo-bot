"""Full-list All-TA pair scan for the Backtest tab (keeps losers; verbose progress)."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

import pandas as pd

from trendalgo.backtest.heartbeat_tf import sort_timeframes
from trendalgo.backtest.load_days import days_for_timeframe
from trendalgo.backtest.ohlcv_resample import frames_from_1h
from trendalgo.backtest.oracle_catalog_coincidence import coincidence_sauce_row
from trendalgo.backtest.ta_fleet import MIN_BARS_FLOOR, buy_and_hold_row, oracle_max_row
from trendalgo.device import strings as S
from trendalgo.device.pair_strategy_pass2 import run_catalog_pass2
from trendalgo.device.pair_strategy_rows import (
    collapse_bh_rows,
    dedupe_indicator_tf,
    ensure_full_catalog,
    remember_skip,
    skip_placeholder_row,
    sort_rows_by_net,
)
from trendalgo.device.pair_strategy_secret_sauce import (
    current_lab_sauce,
    lab_oracle_row,
    mine_and_eval_secret_sauce,
    pending_sauce_row,
    refine_sauce_from_peers,
    upsert_secret_sauce,
    upsert_secret_sauce_ta,
    validate_sauce_against_peers,
)
from trendalgo.device.scanner_all_ta_prune import deepen_seeds, fleet_row_to_lts
from trendalgo.device.scanner_tsl_seeds import best_signal_per_strategy, select_tsl_seeds

# Re-export row helpers for existing imports.
__all__ = [
    "collapse_bh_rows",
    "dedupe_indicator_tf",
    "ensure_full_catalog",
    "scan_pair_strategies",
    "skip_placeholder_row",
    "sort_rows_by_net",
]

ProgressFn = Callable[[dict[str, Any]], None]
RowsFn = Callable[[list[dict[str, Any]]], None]

# Sauce TA + Lab after catalog — keep the bar under 100% until both finish.
SAUCE_PROGRESS_STEPS = 2


def scan_pair_strategies(
    *,
    symbol: str,
    pair: str,
    timeframes: tuple[str, ...],
    strat_list: tuple[str, ...],
    stake: float,
    fee: Any,
    loader: Any,
    gecko_id: str | None = None,
    on_progress: ProgressFn | None = None,
    on_rows: RowsFn | None = None,
) -> list[dict[str, Any]]:
    """Signal-only all TF → best TF → params → TSL grid (trades ≥ 3)."""
    out: list[dict[str, Any]] = []
    skip_best: dict[str, str] = {}
    load_symbol = pair.split("/", 1)[0].strip().upper() if "/" in pair else symbol
    load_symbol = (load_symbol or symbol).upper()
    ordered_tf = sort_timeframes(timeframes)
    catalog_budget = max(1, len(ordered_tf) * max(1, len(strat_list)))
    total = catalog_budget + SAUCE_PROGRESS_STEPS
    done = 0
    frames_by_tf: dict[str, pd.DataFrame] = {}

    def emit(message: str, **extra: Any) -> None:
        if on_progress is not None:
            on_progress({"message": message, "done": done, "total": total, **extra})

    def publish() -> None:
        if on_rows is not None:
            on_rows(list(out))

    lookback_days = days_for_timeframe("1h")
    emit(
        f"Loading {load_symbol} 1h ({lookback_days}d) once, then resampling…",
        phase="load",
        timeframe="1h",
    )
    loaded_1h = loader.load(
        symbol=load_symbol,
        timeframe="1h",
        days=lookback_days,
        gecko_id=gecko_id,
    )
    if loaded_1h.frame is None or loaded_1h.frame.empty:
        emit(f"No 1h candles for {load_symbol}", phase="load", timeframe="1h")
        for sid in strat_list:
            remember_skip(skip_best, sid, "insufficient_bars")
        done = total
        out = ensure_full_catalog(out, strat_list, symbol=symbol, stake_usd=stake, skips=skip_best)
        publish()
        emit(f"Scan complete — {len(out)} rows", phase="done", done=total)
        return out

    frame_1h = loaded_1h.frame
    emit(
        f"Resampling {load_symbol} 1h ({len(frame_1h)} bars) → {len(ordered_tf)} timeframes…",
        phase="load",
        timeframe="1h",
    )
    resampled = frames_from_1h(frame_1h, ordered_tf)

    for timeframe in ordered_tf:
        frame = resampled.get(timeframe)
        if frame is None or frame.empty or len(frame) < MIN_BARS_FLOOR:
            n_bars = 0 if frame is None else len(frame)
            emit(
                f"{timeframe}: {n_bars} bars (<{MIN_BARS_FLOOR}) — "
                f"using lower-TF results for indicators",
                phase="load",
                timeframe=timeframe,
            )
            continue
        frames_by_tf[timeframe] = frame
        emit(
            f"{timeframe}: {len(frame)} bars (from 1h · {lookback_days}d)",
            phase="load",
            timeframe=timeframe,
        )
        bh = buy_and_hold_row(frame, lookback_seconds=0, stake_usd=stake, fee=fee)
        if bh is not None:
            bh = dict(bh)
            bh["timeframe"] = timeframe
            out.append(fleet_row_to_lts(bh, symbol=symbol, stake_usd=stake, is_bh=True))
            emit(f"{timeframe} B&H recorded", phase="bh", timeframe=timeframe)
        oracle = oracle_max_row(frame, lookback_seconds=0, stake_usd=stake, fee=fee)
        if oracle is not None:
            oracle = dict(oracle)
            oracle["timeframe"] = timeframe
            out.append(fleet_row_to_lts(oracle, symbol=symbol, stake_usd=stake, is_oracle=True))
            emit(f"{timeframe} Oracle max recorded", phase="oracle", timeframe=timeframe)
        publish()

    ss_future: Future[dict[str, Any] | None] | None = None
    ss_pool: ThreadPoolExecutor | None = None
    t_ss_start = time.perf_counter()
    lab_oracle = lab_oracle_row(out)
    if lab_oracle is not None:
        ss_tf = str(lab_oracle.get("timeframe") or "1h")
        out.append(pending_sauce_row(symbol=symbol, timeframe=ss_tf, stake=stake))
        publish()
        emit(
            f"Secret Sauce Lab started on {ss_tf} (overlaps catalog TA)…",
            phase="sauce",
            ss_lab_pending=True,
            ss_tf=ss_tf,
        )
        ss_pool = ThreadPoolExecutor(max_workers=1)
        ss_future = ss_pool.submit(
            mine_and_eval_secret_sauce,
            lab_oracle,
            frames_by_tf=frames_by_tf,
            symbol=symbol,
            stake=stake,
            fee=fee,
        )

    def _on_tf(_tf: str, batch: list[dict[str, Any]]) -> None:
        for row in batch:
            out.append(fleet_row_to_lts(row, symbol=symbol, stake_usd=stake))
        publish()

    signal_rows, pass2_skips, done = run_catalog_pass2(
        frames_by_tf=frames_by_tf,
        ordered_tf=ordered_tf,
        strat_list=strat_list,
        fee=fee,
        stake=stake,
        done_start=done,
        total=total,
        on_progress=on_progress,
        on_tf_rows=_on_tf,
    )
    for sid, reason in pass2_skips.items():
        remember_skip(skip_best, sid, reason)

    winners = best_signal_per_strategy(signal_rows)
    seeds = select_tsl_seeds(winners)
    if seeds and frames_by_tf:
        emit(
            f"Deepening {len(seeds)} indicator(s) (params @ signal-only → TSL 1–20%)…",
            phase="tsl-grid",
        )

        def deepen_line(msg: str) -> None:
            emit(msg, phase="tsl-grid")

        fallback = next(iter(frames_by_tf.values()))
        for best in deepen_seeds(
            fallback,
            seeds,
            fee=fee,
            stake_usd=stake,
            timeframe=str(seeds[0].get("timeframe") or "1h"),
            frames_by_tf=frames_by_tf,
            on_progress=deepen_line,
        ):
            out.append(fleet_row_to_lts(best, symbol=symbol, stake_usd=stake))
            publish()

    out = dedupe_indicator_tf(out)
    out = ensure_full_catalog(out, strat_list, symbol=symbol, stake_usd=stake, skips=skip_best)
    publish()
    # Catalog budget used; Sauce steps still pending (bar must stay < 100%).
    done = min(done, catalog_budget)
    emit(S.SCAN_PHASE_SAUCE_COINCIDENCE, phase="sauce", catalog_ready=True)

    # Secret Sauce TA — catalog coincidence at Oracle bars (live, before Lab).
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
                emit(
                    f"Secret Sauce TA recorded ({coin.get('net_pct')}%)",
                    phase="sauce",
                    ss_coincidence=True,
                )
    done = min(total, done + 1)
    emit(S.SCAN_PHASE_SAUCE_COINCIDENCE + " done", phase="sauce", ss_ta_done=True)

    t_join = time.perf_counter()
    sauce: dict[str, Any] | None = None
    if ss_future is not None:
        if ss_future.done():
            emit("Secret Sauce Lab already done — merging…", phase="sauce")
        else:
            emit("Secret Sauce Lab still cooking (async merge)…", phase="sauce")
        try:
            sauce = ss_future.result()
        except Exception:
            sauce = None
        ss_wait = time.perf_counter() - t_join
        ss_total = time.perf_counter() - t_ss_start
        emit(
            f"{S.SCAN_PHASE_SAUCE_MERGE} total={ss_total:.2f}s wait={ss_wait:.2f}s",
            phase="sauce",
            ss_mine_s=round(ss_total, 3),
            ss_wait_s=round(ss_wait, 3),
        )
    if ss_pool is not None:
        ss_pool.shutdown(wait=False)

    # Secret Sauce Lab — deep refine; never replaces Sauce TA.
    base = sauce if sauce is not None else current_lab_sauce(out)
    if base is not None:
        emit(S.SCAN_PHASE_SAUCE_REFINE, phase="sauce")
        try:
            base = refine_sauce_from_peers(
                base, out, frames_by_tf, stake=stake, fee=fee, time_budget_s=12.0
            )
        except (TypeError, ValueError, KeyError, IndexError):
            pass
        ok, reason = validate_sauce_against_peers(base, out, frames_by_tf, stake=stake, fee=fee)
        base = dict(base)
        base["ss_lab_pending"] = False
        base["spectrum_ok"] = bool(ok)
        if not ok:
            base["spectrum_note"] = reason
        out = upsert_secret_sauce(out, base)
        publish()
        if ok:
            emit("Secret Sauce Lab recorded", phase="sauce")
        else:
            emit(f"Secret Sauce Lab recorded (spectrum: {reason})", phase="sauce")
    else:
        emit("Secret Sauce Lab unavailable — pending stub left for honesty", phase="sauce")
    done = min(total, done + 1)

    emit(f"Scan complete — {len(out)} rows", phase="done", done=total)
    publish()
    return out
