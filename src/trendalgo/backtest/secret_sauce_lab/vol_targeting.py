"""T — volatility-targeted stake scalar (signal unchanged; sizing only)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def vol_target_scalar(df: pd.DataFrame, *, target_atr_pct: float = 0.02) -> float:
    """Return stake multiplier in ~[0.5, 1.5] from recent ATR% vs target."""
    if df.empty or "high" not in df.columns or "low" not in df.columns:
        return 1.0
    high = pd.Series(df["high"].to_numpy(dtype=float), index=df.index, dtype=float)
    low = pd.Series(df["low"].to_numpy(dtype=float), index=df.index, dtype=float)
    close = pd.Series(df["close"].to_numpy(dtype=float), index=df.index, dtype=float)
    prev = close.shift(1)
    tr = pd.concat([(high - low), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    atr = pd.Series(pd.Series(tr, dtype=float).rolling(14, min_periods=5).mean(), dtype=float)
    last_close = float(close.iloc[-1])
    last_atr = float(atr.iloc[-1]) if len(atr) else 0.0
    atr_pct = (last_atr / last_close) if last_close else 0.0
    if atr_pct <= 0 or target_atr_pct <= 0:
        return 1.0
    raw = target_atr_pct / atr_pct
    return float(np.clip(raw, 0.5, 1.5))
