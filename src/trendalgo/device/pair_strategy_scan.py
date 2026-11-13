"""Full-list All-TA pair scan for the Backtest tab (keeps losers; verbose progress)."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd

from trendalgo.backtest.heartbeat_tf import needs_1m_base, sort_timeframes
from trendalgo.backtest.load_days import days_for_timeframe
from trendalgo.backtest.ohlcv_resample import frames_from_base
from trendalgo.backtest.oracle_catalog_coincidence import coincidence_sauce_row
from trendalgo.backtest.ta_fleet import MIN_BARS_FLOOR, buy_and_hold_row, oracle_max_row
from trendalgo.device import strings as S
from trendalgo.device.pair_strategy_pass2 import pass2_worker_count, run_catalog_pass2
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
from trendalgo.device.scan_base_ohlcv import load_base_ohlcv_frame
from trendalgo.device.scan_unit_timing import (
    UnitSample,
    estimate_catalog_wall_s,
    flush_ledger,
    load_ledger,
    record_units,
    top_slowest,
    write_last_run,
)
from trendalgo.device.scanner_all_ta_prune import deepen_seeds, fleet_row_to_lts
from trendalgo.device.scanner_protective_tsl import stamp_rows_protective_tsl
from trendalgo.device.scanner_tsl_seeds import best_signal_per_strategy, select_tsl_seeds
from trendalgo.device.sim_accel_label import warm_tsl_grid_kernels

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

# Sauce TA + Lab + helpers suite + Final — keep bar under 100% until suite finishes.
SAUCE_PROGRESS_STEPS = 4


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
    prefs_root: Path | None = None,
    on_progress: ProgressFn | None = None,
    on_rows: RowsFn | None = None,
    include_sauce: bool = True,
    sauce_only_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Signal-only all TF → best TF → params → TSL grid (trades ≥ 3).

    Returns ``(rows, market_context)`` — context is pair-level, not a strategy row.
    When ``include_sauce`` is false, catalog + deepen + protective TSL only (Opportunity
    pass-1); Secret Sauce Lab / coincidence / helpers are skipped.
    When ``sauce_only_rows`` is set, skip catalog/deepen and cook Sauce on those rows.
    """
    if sauce_only_rows is not None:
        from trendalgo.device.pair_strategy_sauce_pass import run_sauce_only_pass

        return run_sauce_only_pass(
            symbol=symbol,
            pair=pair,
            timeframes=timeframes,
            seed_rows=sauce_only_rows,
            stake=stake,
            fee=fee,
            loader=loader,
            gecko_id=gecko_id,
            prefs_root=prefs_root,
            on_progress=on_progress,
            on_rows=on_rows,
        )
    out: list[dict[str, Any]] = []
    skip_best: dict[str, str] = {}
    market_context: dict[str, Any] | None = None
    load_symbol = pair.split("/", 1)[0].strip().upper() if "/" in pair else symbol
    load_symbol = (load_symbol or symbol).upper()
    ordered_tf = sort_timeframes(timeframes)
    catalog_budget = max(1, len(ordered_tf) * max(1, len(strat_list)))
    total = catalog_budget + (SAUCE_PROGRESS_STEPS if include_sauce else 0)
    done = 0
    frames_by_tf: dict[str, pd.DataFrame] = {}
    load_s = 0.0
    pass1_s = 0.0
    deepen_s = 0.0
    sauce_s = 0.0
    base_tf = "1h"
    base_frame: pd.DataFrame | None = None
    ledger = load_ledger(prefs_root) if prefs_root is not None else None
    catalog_units: list[UnitSample] = []
    remaining_units = [(sid, tf) for tf in ordered_tf for sid in strat_list]
    workers = pass2_worker_count()
    warm_tsl_grid_kernels()

    def _eta_remaining() -> float | None:
        if ledger is None:
            return None
        return estimate_catalog_wall_s(ledger, remaining_units, workers=workers) + (
            ledger.deepen_s + ledger.sauce_s if remaining_units else 0.0
        )

    def emit(message: str, **extra: Any) -> None:
        if on_progress is not None:
            eta = _eta_remaining()
            if eta is not None and "eta_remaining_s" not in extra:
                extra = {**extra, "eta_remaining_s": round(float(eta), 1)}
            on_progress({"message": message, "done": done, "total": total, **extra})

    def _on_unit_timings(samples: list[UnitSample]) -> None:
        nonlocal remaining_units
        catalog_units.extend(samples)
        done_keys = {(u.strategy, u.timeframe) for u in samples}
        remaining_units = [u for u in remaining_units if u not in done_keys]
        if ledger is not None and prefs_root is not None:
            record_units(ledger, samples)
            flush_ledger(prefs_root, ledger)

    def publish() -> None:
        if on_rows is not None:
            on_rows(list(out))

    lookback_days = days_for_timeframe("1h")
    base_hint = "1m" if needs_1m_base(ordered_tf) else "1h"
    emit(
        f"Loading {load_symbol} {base_hint} ({lookback_days}d) once, then resampling…",
        phase="load",
        timeframe=base_hint,
    )
    t_load = time.perf_counter()
    base_frame, base_tf, data_source, cache_age_s = load_base_ohlcv_frame(
        symbol=load_symbol,
        pair=pair,
        timeframes=ordered_tf,
        loader=loader,
        gecko_id=gecko_id,
    )
    load_s = time.perf_counter() - t_load
    if ledger is not None and prefs_root is not None:
        record_units(
            ledger,
            [
                UnitSample(
                    strategy="",
                    timeframe=base_hint,
                    pair=pair,
                    elapsed_s=load_s,
                    phase="load",
                )
            ],
        )
        flush_ledger(prefs_root, ledger)
    if base_frame is None or base_frame.empty:
        emit(f"No {base_tf} candles for {load_symbol}", phase="load", timeframe=base_tf)
        for sid in strat_list:
            remember_skip(skip_best, sid, "insufficient_bars")
        done = total
        out = ensure_full_catalog(out, strat_list, symbol=symbol, stake_usd=stake, skips=skip_best)
        publish()
        emit(f"Scan complete — {len(out)} rows", phase="done", done=total)
        return out, {
            "data_source": data_source,
            "cache_age_s": cache_age_s,
        }

    emit(
        f"Resampling {load_symbol} {base_tf} ({len(base_frame)} bars) → "
        f"{len(ordered_tf)} timeframes…",
        phase="load",
        timeframe=base_tf,
        data_source=data_source,
        cache_age_s=cache_age_s,
    )
    resampled = frames_from_base(base_frame, ordered_tf)

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
            f"{timeframe}: {len(frame)} bars (from {base_tf} · {lookback_days}d)",
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

    # Pair-level Market Context (primary TF or first loaded frame) — not a strategy row.
    try:
        from trendalgo.analytics.market_context import compute_market_context

        primary = frames_by_tf.get("1h")
        if primary is None:
            primary = frames_by_tf.get("4h")
        if primary is None and frames_by_tf:
            primary = next(iter(frames_by_tf.values()))
        if primary is not None and not primary.empty:
            market_context = compute_market_context(primary).to_dict()
    except Exception as exc:
        emit(f"Market Context soft-fail: {exc}", phase="load")
        market_context = None
    if market_context is None:
        from trendalgo.analytics.market_context import MarketContext

        market_context = MarketContext.empty("unavailable").to_dict()
    market_context["data_source"] = data_source
    market_context["cache_age_s"] = cache_age_s

    ss_future: Future[dict[str, Any] | None] | None = None
    ss_pool: ThreadPoolExecutor | None = None
    t_ss_start = time.perf_counter()
    lab_oracle = lab_oracle_row(out) if include_sauce else None
    if include_sauce and lab_oracle is not None:
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

    t_pass1 = time.perf_counter()
    signal_rows, pass2_skips, done, pass2_units = run_catalog_pass2(
        frames_by_tf=frames_by_tf,
        ordered_tf=ordered_tf,
        strat_list=strat_list,
        fee=fee,
        stake=stake,
        done_start=done,
        total=total,
        pair=pair,
        on_progress=on_progress,
        on_tf_rows=_on_tf,
        on_unit_timings=_on_unit_timings if prefs_root is not None else None,
    )
    pass1_s = time.perf_counter() - t_pass1
    if pass2_units:
        if not catalog_units:
            catalog_units.extend(pass2_units)
        done_keys = {(u.strategy, u.timeframe) for u in pass2_units}
        remaining_units = [u for u in remaining_units if u not in done_keys]
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
        t_deepen = time.perf_counter()
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
        deepen_s = time.perf_counter() - t_deepen
        if ledger is not None and prefs_root is not None:
            record_units(
                ledger,
                [
                    UnitSample(
                        strategy="",
                        timeframe="",
                        pair=pair,
                        elapsed_s=deepen_s,
                        phase="deepen",
                    )
                ],
            )
            flush_ledger(prefs_root, ledger)

    out = dedupe_indicator_tf(out)
    out = ensure_full_catalog(out, strat_list, symbol=symbol, stake_usd=stake, skips=skip_best)
    publish()
    # Catalog budget used; Sauce steps still pending when include_sauce (bar < 100%).
    # Protective TSL stamped once at the end (avoids 3× full grids).
    done = min(done, catalog_budget)
    remaining_units = []
    t_sauce = time.perf_counter()
    if not include_sauce:
        emit("Sauce skipped (Opportunity catalog pass)", phase="sauce", catalog_ready=True)
        out = stamp_rows_protective_tsl(out, frames_by_tf, fee=fee, stake=stake)
        publish()
        sauce_s = 0.0
        if ledger is not None and prefs_root is not None:
            slow = top_slowest(catalog_units, 20)
            write_last_run(
                prefs_root,
                {
                    "pair": pair,
                    "workers": workers,
                    "phase_s": {
                        "load_s": round(load_s, 3),
                        "pass1_s": round(pass1_s, 3),
                        "deepen_s": round(deepen_s, 3),
                        "sauce_s": 0.0,
                    },
                    "top_units": [
                        {
                            "strategy": u.strategy,
                            "timeframe": u.timeframe,
                            "elapsed_s": round(u.elapsed_s, 3),
                        }
                        for u in slow
                    ],
                },
            )
        if market_context is None:
            market_context = {}
        market_context["phase_s"] = {
            "load_s": round(load_s, 3),
            "pass1_s": round(pass1_s, 3),
            "deepen_s": round(deepen_s, 3),
            "sauce_s": 0.0,
        }
        market_context["include_sauce"] = False
        emit(
            f"Scan complete — {len(out)} rows",
            phase="done",
            done=total,
            load_s=round(load_s, 3),
            base_tf=base_tf,
            bars_base=0 if base_frame is None else len(base_frame),
            n_strategies=len(strat_list),
            n_timeframes=len(ordered_tf),
            had_subhour=needs_1m_base(ordered_tf),
            eta_remaining_s=0.0,
        )
        publish()
        return out, market_context

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
        except Exception as exc:
            sauce = None
            emit(f"Secret Sauce Lab mine failed: {exc}", phase="sauce")
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
    from trendalgo.device.pair_strategy_secret_sauce import unavailable_lab_row

    base = sauce if sauce is not None else current_lab_sauce(out)
    if base is not None:
        emit(S.SCAN_PHASE_SAUCE_REFINE, phase="sauce")
        try:
            base = refine_sauce_from_peers(base, out, frames_by_tf, stake=stake, fee=fee)
        except (TypeError, ValueError, KeyError, IndexError):
            pass
        ok, reason = validate_sauce_against_peers(base, out, frames_by_tf, stake=stake, fee=fee)
        # Always publish a mined recipe (spectrum_fail = honesty flag, not delete).
        # Unavailable is only for mine/exception miss below.
        base = dict(base)
        base["ss_lab_pending"] = False
        base["ss_unavailable"] = False
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
        # Never leave "still cooking…" after the scan finishes.
        ss_tf = str((lab_oracle or {}).get("timeframe") or "1h") if lab_oracle else "1h"
        note = "no fee-honest Lab recipe on this window"
        stub = unavailable_lab_row(symbol=symbol, timeframe=ss_tf, stake=stake, reason=note)
        out = upsert_secret_sauce(out, stub)
        publish()
        emit(f"Secret Sauce Lab unavailable — {note}", phase="sauce")
    done = min(total, done + 1)
    emit("Secret Sauce helpers cooking…", phase="sauce", ss_helpers=True)

    # Helpers + Final Boss (A/B/C/E + S5–S6 suite) — uncapped; progress per helper.
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
        publish()
    done = min(total, done + 1)
    emit("Secret Sauce Final / helpers done", phase="sauce", ss_final_done=True)
    done = min(total, done + 1)

    out = stamp_rows_protective_tsl(out, frames_by_tf, fee=fee, stake=stake)
    publish()

    sauce_s = time.perf_counter() - t_sauce
    if ledger is not None and prefs_root is not None:
        record_units(
            ledger,
            [
                UnitSample(
                    strategy="",
                    timeframe="",
                    pair=pair,
                    elapsed_s=sauce_s,
                    phase="sauce",
                )
            ],
        )
        flush_ledger(prefs_root, ledger)
        slow = top_slowest(catalog_units, 20)
        write_last_run(
            prefs_root,
            {
                "pair": pair,
                "workers": workers,
                "phase_s": {
                    "load_s": round(load_s, 3),
                    "pass1_s": round(pass1_s, 3),
                    "deepen_s": round(deepen_s, 3),
                    "sauce_s": round(sauce_s, 3),
                },
                "top_units": [
                    {
                        "strategy": u.strategy,
                        "timeframe": u.timeframe,
                        "elapsed_s": round(u.elapsed_s, 3),
                    }
                    for u in slow
                ],
            },
        )
    if market_context is None:
        market_context = {}
    market_context["phase_s"] = {
        "load_s": round(load_s, 3),
        "pass1_s": round(pass1_s, 3),
        "deepen_s": round(deepen_s, 3),
        "sauce_s": round(sauce_s, 3),
    }
    market_context["include_sauce"] = True
    emit(
        f"Scan complete — {len(out)} rows",
        phase="done",
        done=total,
        load_s=round(load_s, 3),
        base_tf=base_tf,
        bars_base=0 if base_frame is None else len(base_frame),
        n_strategies=len(strat_list),
        n_timeframes=len(ordered_tf),
        had_subhour=needs_1m_base(ordered_tf),
        eta_remaining_s=0.0,
    )
    publish()
    return out, market_context
