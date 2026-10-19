"""GEN_SECRET entry+exit evaluation (no 1-bar roll)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_features import (
    entries_for_secret_sauce,
    masks_for_secret_sauce,
)
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def eval_gen_secret(
    df: pd.DataFrame,
    strategy_id: str,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    *,
    timeframe: str,
    lookback_seconds: int,
    params: dict[str, Any],
    trailing_stop_pct: float,
    phase: str,
    collect_trades: bool,
    row_from_stats: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    entry_c = tuple(_parse(_secret_entry(params)))
    exit_c = tuple(_parse(_secret_exit(params)))
    if not entry_c:
        return None, "no_trades"
    if exit_c:
        entries, exits = masks_for_secret_sauce(df, entry_conjuncts=entry_c, exit_conjuncts=exit_c)
    else:
        rule = CompositeRule(strategy_id=strategy_id.upper(), conjuncts=entry_c, rationale="")
        entries = entries_for_secret_sauce(df, rule)
        exits = np.zeros(len(df), dtype=bool)
    if not entries.any():
        return None, "no_trades"
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
    slim = {
        "strategy_id": strategy_id,
        "entry_conjuncts": [{"feature": c.feature, "op": c.op, "value": c.value} for c in entry_c],
        "exit_conjuncts": [{"feature": c.feature, "op": c.op, "value": c.value} for c in exit_c],
        "rationale": str(params.get("rationale") or ""),
    }
    return (
        row_from_stats(
            stats,
            strategy_id=strategy_id,
            timeframe=timeframe,
            lookback_seconds=lookback_seconds,
            params=slim,
            phase=phase,
            bar_count=len(df),
        ),
        None,
    )


def _legacy(params: dict[str, Any]) -> list[Any]:
    raw = params.get("conjuncts")
    if raw is None and isinstance(params.get("rule"), dict):
        raw = params["rule"].get("conjuncts")
    return raw if isinstance(raw, list) else []


def _secret_entry(params: dict[str, Any]) -> list[Any]:
    raw = params.get("entry_conjuncts")
    if isinstance(raw, list) and raw:
        return raw
    return _legacy(params)


def _secret_exit(params: dict[str, Any]) -> list[Any]:
    raw = params.get("exit_conjuncts")
    return raw if isinstance(raw, list) else []


def _parse(raw: list[Any]) -> list[RuleConjunct]:
    out: list[RuleConjunct] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(
                RuleConjunct(
                    feature=str(item.get("feature") or ""),
                    op=str(item.get("op") or ">="),
                    value=float(item.get("value") or 0.0),
                )
            )
    return out
