"""Pandas-only fallbacks for indicators when TA-Lib is not installed."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd

from trendalgo.strategies.runtime.indicators import close_series, sma


def _wilder_rma(series: pd.Series, period: int) -> pd.Series:
    return cast(pd.Series, series.ewm(alpha=1 / period, adjust=False, min_periods=period).mean())


def _true_range(df: pd.DataFrame) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    prev_close = df["close"].astype(float).shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    )
    return cast(pd.Series, ranges.max(axis=1))


def _directional_movement(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(
        np.where((up > down) & (up > 0), up, 0.0),
        index=df.index,
        dtype=float,
    )
    minus_dm = pd.Series(
        np.where((down > up) & (down > 0), down, 0.0),
        index=df.index,
        dtype=float,
    )
    return plus_dm, minus_dm


def compute_bbands(df: pd.DataFrame, **params: Any) -> dict[str, np.ndarray]:
    period = int(params.get("timeperiod", 20))
    nbdevup = float(params.get("nbdevup", 2.0))
    nbdevdn = float(params.get("nbdevdn", 2.0))
    c = close_series(df)
    mid = sma(c, period)
    std = c.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + nbdevup * std
    lower = mid - nbdevdn * std
    return {
        "upper": upper.to_numpy(dtype=float),
        "middle": mid.to_numpy(dtype=float),
        "lower": lower.to_numpy(dtype=float),
    }


def compute_plus_di(df: pd.DataFrame, **params: Any) -> dict[str, np.ndarray]:
    period = int(params.get("timeperiod", 14))
    plus_dm, _minus_dm = _directional_movement(df)
    tr = _true_range(df)
    ratio = _wilder_rma(plus_dm, period) / _wilder_rma(tr, period).replace(0, np.nan)
    di = cast(pd.Series, 100.0 * ratio)
    return {"value": di.to_numpy(dtype=float)}


def compute_minus_di(df: pd.DataFrame, **params: Any) -> dict[str, np.ndarray]:
    period = int(params.get("timeperiod", 14))
    _plus_dm, minus_dm = _directional_movement(df)
    tr = _true_range(df)
    ratio = _wilder_rma(minus_dm, period) / _wilder_rma(tr, period).replace(0, np.nan)
    di = cast(pd.Series, 100.0 * ratio)
    return {"value": di.to_numpy(dtype=float)}


def compute_sar(df: pd.DataFrame, **params: Any) -> dict[str, np.ndarray]:
    """Parabolic SAR (Wilder). Enough fidelity for signal smoke without TA-Lib."""
    acceleration = float(params.get("acceleration", 0.02))
    maximum = float(params.get("maximum", 0.2))
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    n = len(df)
    out = np.full(n, np.nan, dtype=float)
    if n < 2:
        return {"value": out}

    long = True
    af = acceleration
    ep = high[0]
    sar = low[0]
    out[0] = sar
    for i in range(1, n):
        prev_sar = sar
        sar = prev_sar + af * (ep - prev_sar)
        if long:
            sar = min(sar, low[i - 1])
            if i >= 2:
                sar = min(sar, low[i - 2])
            if low[i] < sar:
                long = False
                sar = ep
                ep = low[i]
                af = acceleration
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + acceleration, maximum)
        else:
            sar = max(sar, high[i - 1])
            if i >= 2:
                sar = max(sar, high[i - 2])
            if high[i] > sar:
                long = True
                sar = ep
                ep = high[i]
                af = acceleration
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + acceleration, maximum)
        out[i] = sar
    return {"value": out}
