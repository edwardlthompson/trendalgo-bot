"""Second-pass parameter sweep for fleet top-N strategies."""

from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import Any

import pandas as pd

from trendalgo.backtest.fleet_config import OPTIMIZE_MAX_VARIANTS, PASS12_TRAILING_STOP_PCT
from trendalgo.backtest.ta_fleet import backtest_one, default_params
from trendalgo.exchanges.fees import ExchangeFeeSchedule
from trendalgo.ta.param_specs import ta_param_specs

ProgressCb = Callable[[str, dict[str, Any] | None, str | None], None]


def param_variants(strategy_id: str, *, max_variants: int = OPTIMIZE_MAX_VARIANTS) -> list[dict[str, Any]]:
    specs = ta_param_specs(strategy_id)
    base = default_params(strategy_id)
    if not specs:
        return [base]
    axes: list[list[float | int]] = []
    keys: list[str] = []
    for spec in specs:
        lo = float(spec.min if spec.min is not None else spec.default)
        hi = float(spec.max if spec.max is not None else spec.default)
        mid = float(spec.default)
        vals = sorted({lo, mid, hi})
        keys.append(str(spec.key))
        sample = base.get(spec.key, spec.default)
        if isinstance(sample, int):
            axes.append([int(round(v)) for v in vals])
        else:
            axes.append(vals)
    combos: list[dict[str, Any]] = []
    for tup in itertools.product(*axes):
        if len(combos) >= max_variants:
            break
        row = dict(base)
        for key, val in zip(keys, tup, strict=True):
            row[key] = val
        combos.append(row)
    return combos or [base]


def estimate_optimize_combos(rows: list[dict[str, Any]]) -> int:
    return sum(len(param_variants(str(r["strategy_id"]))) for r in rows)


def optimize_top_rows(
    rows: list[dict[str, Any]],
    ohlcv_by_tf: dict[str, list[dict[str, Any]]],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    pair: str,
    fetch_tf_by_tv: dict[str, str],
    lookback_seconds: int,
    trailing_stop_pct: float = PASS12_TRAILING_STOP_PCT,
    on_trial: ProgressCb | None = None,
) -> list[dict[str, Any]]:
    optimized: list[dict[str, Any]] = []
    for seed in rows:
        tv_tf = str(seed["timeframe"])
        ohlcv = ohlcv_by_tf.get(tv_tf)
        if not ohlcv:
            continue
        fetch_tf = fetch_tf_by_tv[tv_tf]
        df = _ohlcv_df(ohlcv, pair=pair, fetch_tf=fetch_tf)
        best = dict(seed)
        best_variants = param_variants(str(seed["strategy_id"]))
        for params in best_variants:
            trial, reason = backtest_one(
                df,
                str(seed["strategy_id"]),
                fee,
                stake_usd,
                timeframe=tv_tf,
                lookback_seconds=lookback_seconds,
                params=params,
                trailing_stop_pct=trailing_stop_pct,
                phase="optimize",
            )
            label = f"opt {seed['strategy_id']}@{tv_tf} {params}"
            on_trial and on_trial(label, trial, reason)
            if trial and trial["net_profit"] > best.get("net_profit", float("-inf")):
                best = {
                    **trial,
                    "optimized": True,
                    "baseline_net_profit": seed.get("net_profit"),
                    "baseline_params": seed.get("params"),
                }
        optimized.append(best)
    optimized.sort(key=lambda r: r["net_profit"], reverse=True)
    for i, row in enumerate(optimized):
        row["rank"] = i + 1
    return optimized


def _ohlcv_df(ohlcv: list[dict[str, Any]], *, pair: str, fetch_tf: str) -> pd.DataFrame:
    from trendalgo.ta.cache import ohlcv_list_to_df

    return ohlcv_list_to_df(ohlcv, pair=pair, fetch_tf=fetch_tf)
