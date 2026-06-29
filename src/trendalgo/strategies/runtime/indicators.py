"""Pandas-only TA helpers for native strategies (no talib required)."""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd


def close_series(df: pd.DataFrame) -> pd.Series:
    """Return the close column as a Series (pyright-safe vs df['close'])."""
    col = df["close"]
    if isinstance(col, pd.DataFrame):
        return col.iloc[:, 0]
    return cast(pd.Series, col)


def ema(series: pd.Series, period: int) -> pd.Series:
    return cast(pd.Series, series.ewm(span=period, adjust=False).mean())


def sma(series: pd.Series, period: int) -> pd.Series:
    return cast(pd.Series, series.rolling(window=period, min_periods=period).mean())


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = cast(pd.Series, 100 - (100 / (1 + rs)))
    return out.astype(float)


def macd(
    series: pd.Series,
    *,
    fastperiod: int = 12,
    slowperiod: int = 26,
    signalperiod: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, histogram (TA-Lib MACD semantics)."""
    fast = ema(series, fastperiod)
    slow = ema(series, slowperiod)
    macd_line = fast - slow
    signal = ema(macd_line, signalperiod)
    hist = macd_line - signal
    return macd_line, signal, hist
