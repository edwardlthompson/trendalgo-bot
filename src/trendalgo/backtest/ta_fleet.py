"""Run TA strategy backtests across timeframes for fleet sweep."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from trendalgo.exchanges.fees import ExchangeFeeSchedule
from trendalgo.backtest.ta_simulator import simulate_buy_and_hold, simulate_long_with_fees
from trendalgo.ta.cache import ohlcv_list_to_df, preset_warmup_bars
from trendalgo.ta.catalog import all_ta_names
from trendalgo.ta.param_specs import ta_param_specs
from trendalgo.ta.signals import resolve_preset, signals_for_preset

MIN_BARS_FLOOR = 50


def default_params(strategy_id: str) -> dict[str, Any]:
    specs = ta_param_specs(strategy_id)
    return {str(s.key): s.default for s in specs}


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
) -> tuple[dict[str, Any] | None, str | None]:
    used_params = dict(params if params is not None else default_params(strategy_id))
    preset = resolve_preset(strategy_id, used_params)
    warmup = preset_warmup_bars(preset)
    if len(df) < max(MIN_BARS_FLOOR, warmup + 10):
        return None, "insufficient_bars"
    try:
        entries, exits = signals_for_preset(df, preset)
    except (KeyError, ValueError, TypeError):
        return None, "compute_error"
    stats = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=stake_usd,
        fee=fee,
        trailing_stop_pct=trailing_stop_pct,
    )
    if stats["trades"] == 0:
        return None, "no_trades"
    return (
        {
            "strategy_id": strategy_id.upper(),
            "timeframe": timeframe,
            "bar_count": len(df),
            "lookback_seconds": lookback_seconds,
            "params": used_params,
            "trailing_stop_pct": trailing_stop_pct,
            "phase": phase,
            **stats,
        },
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


def all_strategies() -> tuple[str, ...]:
    return all_ta_names()


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
