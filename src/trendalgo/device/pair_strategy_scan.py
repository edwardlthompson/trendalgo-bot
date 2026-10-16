"""Full-list All-TA pair scan for the Backtest tab (keeps losers; verbose progress)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from trendalgo.backtest.fleet_config import PASS12_TRAILING_STOP_PCT
from trendalgo.backtest.heartbeat_tf import sort_timeframes
from trendalgo.backtest.load_days import days_for_timeframe
from trendalgo.backtest.ohlcv_resample import frames_from_1h
from trendalgo.backtest.ta_fleet import MIN_BARS_FLOOR, backtest_one, buy_and_hold_row
from trendalgo.device.scanner_all_ta_prune import deepen_seeds, fleet_row_to_lts
from trendalgo.device.scanner_tsl_seeds import best_signal_per_strategy, select_tsl_seeds

ProgressFn = Callable[[dict[str, Any]], None]
_BH = "B&H"
SIGNAL_TSL = float(PASS12_TRAILING_STOP_PCT)


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
) -> list[dict[str, Any]]:
    """Signal-only all TF → best TF → params → TSL grid (trades ≥ 3)."""
    out: list[dict[str, Any]] = []
    skip_best: dict[str, str] = {}
    load_symbol = pair.split("/", 1)[0].strip().upper() if "/" in pair else symbol
    load_symbol = (load_symbol or symbol).upper()
    ordered_tf = sort_timeframes(timeframes)
    total = max(1, len(ordered_tf) * max(1, len(strat_list)))
    done = 0
    frames_by_tf: dict[str, pd.DataFrame] = {}
    signal_rows: list[dict[str, Any]] = []

    def emit(message: str, **extra: Any) -> None:
        if on_progress is not None:
            on_progress({"message": message, "done": done, "total": total, **extra})

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
            _remember_skip(skip_best, sid, "insufficient_bars")
        done = total
        out = ensure_full_catalog(out, strat_list, symbol=symbol, stake_usd=stake, skips=skip_best)
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
            done += len(strat_list)
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

        for index, sid in enumerate(strat_list, start=1):
            done += 1
            emit(
                f"{timeframe} {sid} signal-only ({index}/{len(strat_list)})",
                phase="pass1-signal",
                timeframe=timeframe,
                strategy=sid,
            )
            row, reason = backtest_one(
                frame,
                sid,
                fee,
                stake,
                timeframe=timeframe,
                lookback_seconds=0,
                trailing_stop_pct=SIGNAL_TSL,
            )
            if row is None:
                _remember_skip(skip_best, sid, reason or "compute_error")
                continue
            signal_rows.append(row)
            out.append(fleet_row_to_lts(row, symbol=symbol, stake_usd=stake))
        emit(f"{timeframe} done — {len(out)} rows so far", phase="tf_done", timeframe=timeframe)

    winners = best_signal_per_strategy(signal_rows)
    seeds = select_tsl_seeds(winners)
    if seeds and frames_by_tf:
        emit(
            f"Deepening {len(seeds)} indicator(s) (params @ signal-only → TSL 1–20%)…",
            phase="tsl-grid",
        )

        def deepen_line(msg: str) -> None:
            emit(msg, phase="tsl-grid")

        # Any loaded frame as fallback; deepen_seeds picks seed TF from frames_by_tf.
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

    out = dedupe_indicator_tf(out)
    out = ensure_full_catalog(out, strat_list, symbol=symbol, stake_usd=stake, skips=skip_best)
    emit(f"Scan complete — {len(out)} rows", phase="done", done=total)
    return out


def ensure_full_catalog(
    rows: list[dict[str, Any]],
    strat_list: tuple[str, ...],
    *,
    symbol: str,
    stake_usd: float,
    skips: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """After dedupe, fill missing indicators with honest skip_reason rows (+ keep B&H)."""
    present = {str(r.get("indicator") or "").strip().upper() for r in rows}
    skips = skips or {}
    filled = list(rows)
    for sid in strat_list:
        upper = str(sid).strip().upper()
        if not upper or upper in present or upper == _BH:
            continue
        reason = skips.get(upper) or skips.get(sid) or "no_trades"
        filled.append(
            skip_placeholder_row(upper, symbol=symbol, stake_usd=stake_usd, reason=reason)
        )
        present.add(upper)
    return collapse_bh_rows(filled)


def skip_placeholder_row(
    strategy_id: str,
    *,
    symbol: str,
    stake_usd: float,
    reason: str,
) -> dict[str, Any]:
    """Sheet row for an indicator that was tried but produced no tradable result."""
    stake = float(stake_usd) if stake_usd else 1.0
    return {
        "indicator": strategy_id.upper(),
        "timeframe": "—",
        "params": {},
        "trailing_stop_pct": None,
        "trailing_stop_loss_pct": None,
        "final_equity": stake,
        "net_pct": 0.0,
        "signal_net_pct": 0.0,
        "gross_profit": 0.0,
        "fees_paid": 0.0,
        "fee_taker_pct": None,
        "stake_usd": stake,
        "trades": 0,
        "win_pct": "-",
        "tsl_hits": 0,
        "symbol": symbol,
        "optimized": False,
        "skip_reason": reason,
    }


def _remember_skip(best: dict[str, str], sid: str, reason: str) -> None:
    """Keep the most informative skip reason across TFs."""
    upper = str(sid).strip().upper()
    rank = {
        "compute_error": 0,
        "missing_backend": 1,
        "not_a_strategy": 2,
        "no_pattern": 3,
        "no_trades": 4,
        "insufficient_bars": 5,
    }
    prev = best.get(upper)
    if prev is None or rank.get(reason, 9) < rank.get(prev, 9):
        best[upper] = reason


def collapse_bh_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep a single B&H row — the best Net % — for the Backtest sheet."""
    best_bh: dict[str, Any] | None = None
    best_net = float("-inf")
    others: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("indicator") or "").strip() != _BH:
            others.append(row)
            continue
        try:
            net = float(row.get("net_pct"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            net = float("-inf")
        if net > best_net:
            best_bh, best_net = row, net
    if best_bh is not None:
        others.append(best_bh)
    return others


def dedupe_indicator_tf(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per indicator — best Net % across TFs; prefer optimized on ties."""
    best: dict[str, dict[str, Any]] = {}
    bhs: list[dict[str, Any]] = []
    for row in rows:
        ind = str(row.get("indicator") or "").strip()
        if ind == _BH:
            bhs.append(row)
            continue
        prev = best.get(ind)
        if prev is None or _row_beats(row, prev):
            best[ind] = row
    return collapse_bh_rows(list(best.values()) + bhs)


def sort_rows_by_net(
    rows: list[dict[str, Any]], *, descending: bool = True
) -> list[dict[str, Any]]:
    """Sort by Net % (dir) → Win % desc → fewer TSL hits."""

    def key(row: dict[str, Any]) -> tuple[float, float, float]:
        net = _num(row.get("net_pct"), missing=float("-inf"))
        win = _num(row.get("win_pct"), missing=float("-inf"))
        hits = _num(row.get("tsl_hits"), missing=0.0)
        net_key = net if descending else -net
        return (net_key, win, -hits)

    return sorted(rows, key=key, reverse=True)


def _row_beats(candidate: dict[str, Any], incumbent: dict[str, Any]) -> bool:
    c_net = _num(candidate.get("net_pct"), missing=float("-inf"))
    i_net = _num(incumbent.get("net_pct"), missing=float("-inf"))
    if c_net != i_net:
        return c_net > i_net
    return bool(candidate.get("optimized")) and not bool(incumbent.get("optimized"))


def _num(value: Any, *, missing: float) -> float:
    if value in (None, "-", ""):
        return missing
    try:
        return float(value)
    except (TypeError, ValueError):
        return missing
