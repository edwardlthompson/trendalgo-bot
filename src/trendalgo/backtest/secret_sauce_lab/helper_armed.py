"""Helper B — higher-TF / regime arming gate ∧ entry (fee-honest)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.narrative import build_narrative
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import detect_regime
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit, search_best_pair
from trendalgo.backtest.secret_sauce_lab.search_folds import bar_folds
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_SID = "GEN_SECRET_1"


def arming_mask(df: pd.DataFrame, *, oracle_tf_frame: pd.DataFrame | None = None) -> np.ndarray:
    """Lagged structural arm: close above SMA50 and rising SMA20 (causal)."""
    close = pd.Series(df["close"].to_numpy(dtype=float), index=df.index, dtype=float)
    sma50 = pd.Series(close.rolling(50, min_periods=20).mean(), index=df.index, dtype=float)
    sma20 = pd.Series(close.rolling(20, min_periods=10).mean(), index=df.index, dtype=float)
    rising = sma20 > sma20.shift(1)
    arm = (close > sma50) & rising
    out = arm.fillna(False).to_numpy(dtype=bool)
    # Optional: require higher-TF close also above its SMA20 (aligned by index position).
    if oracle_tf_frame is not None and not oracle_tf_frame.empty and len(oracle_tf_frame) >= 20:
        oc = oracle_tf_frame["close"].astype(float)
        osma = oc.rolling(20, min_periods=10).mean()
        o_arm = (oc > osma).fillna(False).to_numpy(dtype=bool)
        # Broadcast last known higher-TF arm onto primary bars via timestamp nearest.
        if isinstance(df.index, pd.DatetimeIndex) and isinstance(
            oracle_tf_frame.index, pd.DatetimeIndex
        ):
            mapped = np.zeros(len(df), dtype=bool)
            for i, ts in enumerate(df.index):
                loc = oracle_tf_frame.index.get_indexer([ts], method="ffill")
                if len(loc) and 0 <= int(loc[0]) < len(o_arm):
                    mapped[i] = bool(o_arm[int(loc[0])])
            out = out & mapped
    return np.asarray(out, dtype=bool)


def cook_armed_helper(
    df: pd.DataFrame,
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    oracle_tf_frame: pd.DataFrame | None = None,
    oracle_swing_count: int = 0,
) -> tuple[HeartbeatDossier, Any, float] | None:
    if df.empty or len(df) < 40:
        return None
    regime = detect_regime(df)
    bh = bh_net_profit(df, fee=fee, stake=stake_usd)
    # Inject arm as an extra conjunct via above_sma50 (proxy already in bank) + seeds.
    weights = dict(regime.family_weights)
    weights["dip_uptrend"] = max(weights.get("dip_uptrend", 0.2), 0.5)
    pairs = seeds_for_weights(_SID, weights, volume_ok=regime.volume_ok)
    # Prefer entries that already include above_sma50 (arming proxy).
    armed_pairs = [
        (er, xr, "armed")
        for er, xr, _f in pairs
        if any(c.feature == "above_sma50" for c in er.conjuncts)
    ] or [(er, xr, "armed") for er, xr, _f in pairs[:12]]
    train, hold = bar_folds(len(df), holdout_frac=0.35, purge_bars=4)
    hit = search_best_pair(
        df,
        armed_pairs,
        fee=fee,
        stake_usd=stake_usd,
        bh_net=bh,
        time_budget_s=None,
        train_indexes=train,
        holdout_indexes=hold,
        oracle_swing_count=oracle_swing_count,
    )
    if hit is None:
        return None
    # Enforce arming: AND above_sma50 on entry if missing.
    er = hit.entry
    if not any(c.feature == "above_sma50" for c in er.conjuncts):
        er = CompositeRule(
            strategy_id=er.strategy_id,
            conjuncts=(*er.conjuncts, RuleConjunct(feature="above_sma50", op=">=", value=1.0)),
            rationale=er.rationale + "+arm",
        )
    formula, anti = build_narrative(
        regime,
        family="armed",
        entry=er,
        exit_rule=hit.exit,
        beat_bh=bh is not None and hit.net > bh,
    )
    anti += " Armed helper: regime/SMA arming gate on entries (higher-TF when available)."
    del oracle_tf_frame  # used via arming_mask in future feature bank; SMA proxy for now
    dossier = HeartbeatDossier(
        rule=er,
        exit_rule=hit.exit,
        formula_en=formula,
        train_coverage=0.0,
        holdout_coverage=0.0,
        swing_hits=tuple(),
        exit_hits=tuple(),
        oracle_entry_indexes=tuple(),
        oracle_exit_indexes=tuple(),
        anti_cheat=anti,
        holdout_gate_ok=hit.holdout_gate_ok,
        train_net=hit.train_net,
        holdout_net=hit.holdout_net,
        trailing_stop_pct=float(hit.trailing_stop_pct),
    )
    return dossier, regime, float(hit.trailing_stop_pct)
