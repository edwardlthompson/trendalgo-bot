"""Evaluate mined GEN_ORACLE / GEN_SECRET composite rules inside fleet backtests."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import (
    CompositeRule,
    RuleConjunct,
    entries_for_rule,
)
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def backtest_gen_oracle(
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
    """Evaluate a mined GEN_ORACLE / GEN_SECRET composite rule without catalog registration."""
    if strategy_id.upper().startswith("GEN_SECRET"):
        from trendalgo.backtest.gen_secret_eval import eval_gen_secret

        return eval_gen_secret(
            df,
            strategy_id,
            fee,
            stake_usd,
            timeframe=timeframe,
            lookback_seconds=lookback_seconds,
            params=params,
            trailing_stop_pct=trailing_stop_pct,
            phase=phase,
            collect_trades=collect_trades,
            row_from_stats=row_from_stats,
        )
    raw = params.get("conjuncts")
    if raw is None and isinstance(params.get("rule"), dict):
        raw = params["rule"].get("conjuncts")
    if not isinstance(raw, list) or not raw:
        return None, "no_trades"
    conjuncts: list[RuleConjunct] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        conjuncts.append(
            RuleConjunct(
                feature=str(item.get("feature") or ""),
                op=str(item.get("op") or ">="),
                value=float(item.get("value") or 0.0),
            )
        )
    if not conjuncts:
        return None, "no_trades"
    rule = CompositeRule(
        strategy_id=strategy_id.upper(),
        conjuncts=tuple(conjuncts),
        rationale=str(params.get("rationale") or ""),
    )
    entries = entries_for_rule(df, rule)
    if not entries.any():
        return None, "no_trades"
    exits = np.roll(entries, 1)
    exits[0] = False
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
            params=dict(params),
            phase=phase,
            bar_count=len(df),
        ),
        None,
    )
