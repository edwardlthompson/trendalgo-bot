"""Pass 3 — trailing-stop sweep for fleet top-N (0–20% in 2% steps)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from trendalgo.backtest.fleet_config import TSL_SWEEP_PCTS
from trendalgo.backtest.ta_fleet import backtest_one
from trendalgo.exchanges.fees import ExchangeFeeSchedule

ProgressCb = Callable[[str, dict[str, Any] | None, str | None], None]


def estimate_tsl_combos(rows: list[dict[str, Any]]) -> int:
    return len(rows) * len(TSL_SWEEP_PCTS)


def optimize_tsl_for_rows(
    rows: list[dict[str, Any]],
    ohlcv_by_tf: dict[str, list[dict[str, Any]]],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    pair: str,
    fetch_tf_by_tv: dict[str, str],
    lookback_seconds: int,
    on_trial: ProgressCb | None = None,
) -> list[dict[str, Any]]:
    final: list[dict[str, Any]] = []
    for seed in rows:
        tv_tf = str(seed["timeframe"])
        ohlcv = ohlcv_by_tf.get(tv_tf)
        if not ohlcv:
            final.append(dict(seed))
            continue
        fetch_tf = fetch_tf_by_tv[tv_tf]
        df = _ohlcv_df(ohlcv, pair=pair, fetch_tf=fetch_tf)
        params = dict(seed.get("params") or {})
        best = dict(seed)
        best_tsl = float(seed.get("trailing_stop_pct") or 0.0)
        for tsl in TSL_SWEEP_PCTS:
            trial, reason = backtest_one(
                df,
                str(seed["strategy_id"]),
                fee,
                stake_usd,
                timeframe=tv_tf,
                lookback_seconds=lookback_seconds,
                params=params,
                trailing_stop_pct=tsl,
                phase="optimize_tsl",
            )
            label = f"tsl {seed['strategy_id']}@{tv_tf} {tsl * 100:.0f}%"
            on_trial and on_trial(label, trial, reason)
            if trial and trial["net_profit"] > best.get("net_profit", float("-inf")):
                best_tsl = tsl
                best = {
                    **trial,
                    "tsl_optimized": True,
                    "baseline_net_profit_before_tsl": seed.get("net_profit"),
                    "optimal_tsl_pct": tsl,
                }
        if "optimal_tsl_pct" not in best:
            best["optimal_tsl_pct"] = best_tsl
        final.append(best)
    final.sort(key=lambda r: r["net_profit"], reverse=True)
    for i, row in enumerate(final):
        row["rank"] = i + 1
    return final


def _ohlcv_df(ohlcv: list[dict[str, Any]], *, pair: str, fetch_tf: str) -> pd.DataFrame:
    from trendalgo.ta.cache import ohlcv_list_to_df

    return ohlcv_list_to_df(ohlcv, pair=pair, fetch_tf=fetch_tf)
