"""Causal feature bank for Secret Sauce (bars ≤ i only)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_cdl import cdl_feature_keys, merge_cdl_into_rows
from trendalgo.backtest.secret_sauce_cross import (
    CROSS_KEYS,
    compute_rsx_series,
    merge_cross_into_rows,
    osc_cross_columns,
)
from trendalgo.backtest.secret_sauce_pivots import PIVOT_KEYS, merge_pivot_features_into_rows
from trendalgo.backtest.secret_sauce_structure import STRUCTURE_KEYS, merge_structure_into_rows
from trendalgo.backtest.secret_sauce_ta_series import (
    atr_pct,
    bb_pct_b,
    macd_hist,
    rsi,
    stoch_k,
)

PRICE_KEYS = (
    "ret_1",
    "ret_3",
    "ret_5",
    "range_pct",
    "dist_low_5",
    "dist_high_5",
    "local_trough",
    "local_peak",
    "trough_confirm",
    "peak_confirm",
    "above_sma20",
    "above_sma50",
)
VOLUME_KEYS = ("vol_ratio", "vol_ratio_20", "vol_z", "dollar_vol_ratio", "up_vol_impulse")
TA_KEYS = ("rsi_14", "macd_hist", "bb_pct_b", "atr_pct", "stoch_k")
ALL_FEATURE_KEYS = (
    PRICE_KEYS
    + VOLUME_KEYS
    + TA_KEYS
    + CROSS_KEYS
    + STRUCTURE_KEYS
    + PIVOT_KEYS
    + cdl_feature_keys()
)


def has_real_volume(df: pd.DataFrame) -> bool:
    if "volume" not in df.columns or df.empty:
        return False
    vols = df["volume"].to_numpy(dtype=float)
    if not np.isfinite(vols).any():
        return False
    return float(np.nanstd(vols)) > 1e-12 or float(np.nanmax(vols) - np.nanmin(vols)) > 1e-9


def feature_keys_for(df: pd.DataFrame, *, include_pivots: bool = False) -> tuple[str, ...]:
    """Keys for Lab search. Pass include_pivots=True for primary + residual pivot bank."""
    extra = STRUCTURE_KEYS + cdl_feature_keys()
    if include_pivots:
        extra = STRUCTURE_KEYS + PIVOT_KEYS + cdl_feature_keys()
    if has_real_volume(df):
        return PRICE_KEYS + VOLUME_KEYS + TA_KEYS + CROSS_KEYS + extra
    return PRICE_KEYS + TA_KEYS + CROSS_KEYS + extra


def causal_features(df: pd.DataFrame) -> list[dict[str, float]]:
    """Features at bar i use only data at or before i (no future / exit peek)."""
    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float) if "high" in df.columns else closes
    lows = df["low"].to_numpy(dtype=float) if "low" in df.columns else closes
    n = len(df)
    use_vol = has_real_volume(df)
    vols = df["volume"].to_numpy(dtype=float) if use_vol else np.ones(n)
    rsi_a = rsi(closes, 14)
    macd_a = macd_hist(closes)
    bb_a = bb_pct_b(closes, 20)
    atr_a = atr_pct(highs, lows, closes, 14)
    stoch_a = stoch_k(highs, lows, closes, 14)
    out: list[dict[str, float]] = []
    for i in range(n):
        prev = closes[i - 1] if i else closes[i]
        prev3 = closes[i - 3] if i >= 3 else closes[0]
        prev5 = closes[i - 5] if i >= 5 else closes[0]
        lo_w = lows[max(0, i - 5) : i + 1]
        hi_w = highs[max(0, i - 5) : i + 1]
        lo = float(np.min(lo_w))
        hi = float(np.max(hi_w))
        trough = 1.0 if lows[i] <= lo else 0.0
        peak = 1.0 if highs[i] >= hi else 0.0
        # Confirm on next causal bar: prior trough/peak + bounce/fade (no future).
        prev_trough = 0.0
        prev_peak = 0.0
        if i >= 1:
            plo = float(np.min(lows[max(0, i - 1 - 5) : i]))
            phi = float(np.max(highs[max(0, i - 1 - 5) : i]))
            prev_trough = 1.0 if lows[i - 1] <= plo else 0.0
            prev_peak = 1.0 if highs[i - 1] >= phi else 0.0
        trough_confirm = 1.0 if prev_trough >= 1.0 and closes[i] > prev else 0.0
        peak_confirm = 1.0 if prev_peak >= 1.0 and closes[i] < prev else 0.0
        sma20 = float(np.mean(closes[max(0, i - 19) : i + 1]))
        sma50 = float(np.mean(closes[max(0, i - 49) : i + 1]))
        row: dict[str, float] = {
            "ret_1": float((closes[i] / prev - 1.0) if prev else 0.0),
            "ret_3": float((closes[i] / prev3 - 1.0) if prev3 else 0.0),
            "ret_5": float((closes[i] / prev5 - 1.0) if prev5 else 0.0),
            "range_pct": float(((highs[i] - lows[i]) / closes[i]) if closes[i] else 0.0),
            "dist_low_5": float(((closes[i] - lo) / closes[i]) if closes[i] else 0.0),
            "dist_high_5": float(((hi - closes[i]) / closes[i]) if closes[i] else 0.0),
            "local_trough": trough,
            "local_peak": peak,
            "trough_confirm": trough_confirm,
            "peak_confirm": peak_confirm,
            "above_sma20": 1.0 if closes[i] >= sma20 else 0.0,
            "above_sma50": 1.0 if closes[i] >= sma50 else 0.0,
            "rsi_14": float(rsi_a[i]),
            "macd_hist": float(macd_a[i]),
            "bb_pct_b": float(bb_a[i]),
            "atr_pct": float(atr_a[i]),
            "stoch_k": float(stoch_a[i]),
        }
        if use_vol:
            row.update(_volume_at(i, closes, vols, prev))
        out.append(row)
    rsx_a = compute_rsx_series(closes, 14)
    merge_cross_into_rows(out, osc_cross_columns(rsi_a, stoch_a, rsx_a))
    merge_structure_into_rows(closes, highs, lows, out)
    vols_arr = vols if use_vol else None
    merge_pivot_features_into_rows(closes, highs, lows, out, volumes=vols_arr)
    merge_cdl_into_rows(df, out)
    return out


def match_feat(feat: dict[str, float], conjuncts: tuple[RuleConjunct, ...]) -> bool:
    for c in conjuncts:
        val = float(feat.get(c.feature) or 0.0)
        if c.op == ">=" and not (val >= c.value):
            return False
        if c.op == "<=" and not (val <= c.value):
            return False
    return bool(conjuncts)


def entries_for_secret_sauce(df: pd.DataFrame, rule: CompositeRule) -> np.ndarray:
    feats = causal_features(df)
    entries = np.zeros(len(df), dtype=bool)
    for i, feat in enumerate(feats):
        if match_feat(feat, rule.conjuncts):
            entries[i] = True
    return entries


def exits_for_secret_sauce(df: pd.DataFrame, rule: CompositeRule) -> np.ndarray:
    return entries_for_secret_sauce(df, rule)


def masks_for_secret_sauce(
    df: pd.DataFrame,
    *,
    entry_conjuncts: tuple[RuleConjunct, ...],
    exit_conjuncts: tuple[RuleConjunct, ...],
) -> tuple[np.ndarray, np.ndarray]:
    from trendalgo.backtest.oracle_pattern_mine import CompositeRule
    from trendalgo.backtest.secret_sauce_lab.rsx_neighborhood import (
        is_rsx_neighborhood_rule,
        masks_for_rsx_rules,
    )

    entry_rule = CompositeRule(strategy_id="GEN_SECRET_1", conjuncts=entry_conjuncts, rationale="")
    exit_rule = CompositeRule(strategy_id="GEN_SECRET_1", conjuncts=exit_conjuncts, rationale="")
    if is_rsx_neighborhood_rule(entry_rule):
        packed = masks_for_rsx_rules(df, entry_rule, exit_rule)
        if packed is not None:
            return packed
    feats = causal_features(df)
    n = len(df)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    for i, feat in enumerate(feats):
        if match_feat(feat, entry_conjuncts):
            entries[i] = True
        if match_feat(feat, exit_conjuncts):
            exits[i] = True
    return entries, exits


def _volume_at(i: int, closes: np.ndarray, vols: np.ndarray, prev: float) -> dict[str, float]:
    vol_ma5 = float(np.mean(vols[max(0, i - 5) : i + 1]))
    vol_ma20 = float(np.mean(vols[max(0, i - 20) : i + 1]))
    vol_ratio = float(vols[i] / vol_ma5) if vol_ma5 else 1.0
    window = vols[max(0, i - 20) : i + 1]
    v_std = float(np.std(window)) if len(window) > 1 else 0.0
    v_mean = float(np.mean(window)) if len(window) else 0.0
    dv = closes[i] * vols[i]
    dv_ma = float(np.mean(closes[max(0, i - 5) : i + 1] * vols[max(0, i - 5) : i + 1]))
    up = 1.0 if closes[i] >= prev else 0.0
    return {
        "vol_ratio": vol_ratio,
        "vol_ratio_20": float(vols[i] / vol_ma20) if vol_ma20 else 1.0,
        "vol_z": float((vols[i] - v_mean) / v_std) if v_std else 0.0,
        "dollar_vol_ratio": float(dv / dv_ma) if dv_ma else 1.0,
        "up_vol_impulse": float(vol_ratio * up - vol_ratio * (1.0 - up)),
    }
