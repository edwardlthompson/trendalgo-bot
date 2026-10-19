"""Run TA strategy backtests across timeframes for fleet sweep."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.ta_simulator import (
    simulate_buy_and_hold,
    simulate_long_with_fees,
    simulate_oracle_max_gain,
)
from trendalgo.exchanges.fees import ExchangeFeeSchedule
from trendalgo.ta.cache import ohlcv_list_to_df, preset_warmup_bars
from trendalgo.ta.pandas_ta_catalog import is_pandas_ta_indicator, pandas_ta_available
from trendalgo.ta.param_specs import ta_param_specs
from trendalgo.ta.signal_kinds import signal_kind
from trendalgo.ta.signals import resolve_preset, signals_for_preset

MIN_BARS_FLOOR = 50


def default_params(strategy_id: str) -> dict[str, Any]:
    specs = ta_param_specs(strategy_id)
    return {str(s.key): s.default for s in specs}


def prepare_signals(
    df: pd.DataFrame,
    strategy_id: str,
    params: dict[str, Any] | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]] | tuple[None, None, str]:
    """Compute entry/exit arrays once for reuse across TSL trials."""
    used_params = dict(params if params is not None else default_params(strategy_id))
    if signal_kind(strategy_id) == "math_skip":
        return None, None, "not_a_strategy"
    if is_pandas_ta_indicator(strategy_id) and not pandas_ta_available():
        return None, None, "missing_backend"
    preset = resolve_preset(strategy_id, used_params)
    warmup = preset_warmup_bars(preset)
    if len(df) < max(MIN_BARS_FLOOR, warmup + 10):
        return None, None, "insufficient_bars"
    try:
        entries, exits = signals_for_preset(df, preset)
    except (KeyError, ValueError, TypeError, IndexError, AttributeError, RuntimeError):
        # pandas-ta / TA-Lib can raise IndexError (e.g. QQE on short frames).
        return None, None, "compute_error"
    if not entries.any():
        # CDL rarity vs structural zero — distinguish when kind is cdl_pattern.
        if preset.get("kind") == "cdl_pattern":
            return None, None, "no_pattern"
    return entries, exits, used_params


def row_from_stats(
    stats: dict[str, Any],
    *,
    strategy_id: str,
    timeframe: str,
    lookback_seconds: int,
    params: dict[str, Any],
    phase: str,
    bar_count: int,
) -> dict[str, Any]:
    return {
        "strategy_id": strategy_id.upper(),
        "timeframe": timeframe,
        "bar_count": bar_count,
        "lookback_seconds": lookback_seconds,
        "params": params,
        "trailing_stop_pct": float(stats.get("trailing_stop_pct") or 0.0),
        "phase": phase,
        **stats,
    }


def backtest_one(
    df: pd.DataFrame,
    strategy_id: str,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    *,
    timeframe: str,
    lookback_seconds: int,
    params: dict[str, Any] | None = None,
    trailing_stop_pct: float = 0.0,
    phase: str = "pass1",
    collect_trades: bool = False,
) -> tuple[dict[str, Any] | None, str | None]:
    sid_u = str(strategy_id).upper()
    if sid_u.startswith("GEN_ORACLE") or sid_u.startswith("GEN_SECRET"):
        from trendalgo.backtest.gen_oracle_eval import backtest_gen_oracle

        return backtest_gen_oracle(
            df,
            strategy_id,
            fee,
            stake_usd,
            timeframe=timeframe,
            lookback_seconds=lookback_seconds,
            params=params or {},
            trailing_stop_pct=trailing_stop_pct,
            phase=phase,
            collect_trades=collect_trades,
            row_from_stats=row_from_stats,
        )
    prepared = prepare_signals(df, strategy_id, params)
    entries, exits, used_or_err = prepared
    if entries is None or exits is None:
        return None, str(used_or_err)
    used_params = used_or_err if isinstance(used_or_err, dict) else {}
    stats = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=stake_usd,
        fee=fee,
        trailing_stop_pct=trailing_stop_pct,
        collect_trades=collect_trades,
    )
    if stats["trades"] == 0:
        return None, "no_trades"
    return (
        row_from_stats(
            stats,
            strategy_id=strategy_id,
            timeframe=timeframe,
            lookback_seconds=lookback_seconds,
            params=used_params,
            phase=phase,
            bar_count=len(df),
        ),
        None,
    )


def buy_and_hold_row(
    df: pd.DataFrame,
    *,
    lookback_seconds: int,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
) -> dict[str, Any] | None:
    row = simulate_buy_and_hold(df, stake_usd=stake_usd, fee=fee)
    if row is None:
        return None
    row["lookback_seconds"] = lookback_seconds
    return row


def oracle_max_row(
    df: pd.DataFrame,
    *,
    lookback_seconds: int,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
) -> dict[str, Any] | None:
    row = simulate_oracle_max_gain(df, stake_usd=stake_usd, fee=fee)
    if row is None:
        return None
    row["lookback_seconds"] = lookback_seconds
    return row


def run_timeframe_slice(
    ohlcv: list[dict[str, Any]],
    *,
    strategies: tuple[str, ...],
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    timeframe: str,
    lookback_seconds: int,
    pair: str,
    fetch_tf: str,
    trailing_stop_pct: float = 0.0,
    on_strategy: Callable[[str, dict[str, Any] | None, str | None], None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if len(ohlcv) < MIN_BARS_FLOOR:
        return [], {"insufficient_bars": len(strategies)}
    df = ohlcv_list_to_df(ohlcv, pair=pair, fetch_tf=fetch_tf)
    results: list[dict[str, Any]] = []
    skips: dict[str, int] = {"compute_error": 0, "insufficient_bars": 0, "no_trades": 0}
    for sid in strategies:
        row, reason = backtest_one(
            df,
            sid,
            fee,
            stake_usd,
            timeframe=timeframe,
            lookback_seconds=lookback_seconds,
            trailing_stop_pct=trailing_stop_pct,
        )
        on_strategy and on_strategy(sid, row, reason)
        if row is None:
            key = reason or "compute_error"
            skips[key] = skips.get(key, 0) + 1
            continue
        results.append(row)
    return results, skips


def merge_rank(results: list[dict[str, Any]], *, top_n: int = 100) -> list[dict[str, Any]]:
    ranked = sorted(results, key=lambda r: r["net_profit"], reverse=True)
    for i, row in enumerate(ranked):
        row["rank"] = i + 1
    return ranked[:top_n]


def filter_beats_buy_hold(
    rows: list[dict[str, Any]],
    buy_hold: dict[str, Any] | None,
    *,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    """Keep rows with positive net_profit that beat buy-and-hold when set."""
    if not rows:
        return []
    bh_net: float | None = None
    if buy_hold is not None and buy_hold.get("net_profit") is not None:
        bh_net = float(buy_hold["net_profit"])
    trimmed = [
        dict(r)
        for r in rows
        if float(r.get("net_profit", float("-inf"))) > 0.0
        and (bh_net is None or float(r.get("net_profit", float("-inf"))) > bh_net)
    ]
    if top_n is not None:
        trimmed = trimmed[:top_n]
    for i, row in enumerate(trimmed, start=1):
        row["rank"] = i
    return trimmed


def all_strategies() -> tuple[str, ...]:
    """Tradeable All-TA pool only (excludes chart/math/reference TA-Lib helpers)."""
    from trendalgo.ta.strategy_pool import trade_strategy_names

    return trade_strategy_names()


def group_by_strategy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        sid = row["strategy_id"]
        if sid not in best or row["net_profit"] > best[sid]["net_profit"]:
            best[sid] = row
    return sorted(best.values(), key=lambda r: r["net_profit"], reverse=True)


def group_by_timeframe(rows: list[dict[str, Any]], timeframe: str) -> list[dict[str, Any]]:
    filtered = [r for r in rows if r["timeframe"] == timeframe]
    return sorted(filtered, key=lambda r: r["net_profit"], reverse=True)
