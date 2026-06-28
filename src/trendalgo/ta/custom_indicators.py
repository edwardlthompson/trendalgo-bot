"""Custom Fibonacci level indicators (not in TA-Lib or pandas-ta-classic)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    need = ("open", "high", "low", "close", "volume")
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"missing OHLCV columns: {missing}")
    return df


def fibonacci_retrace(df: pd.DataFrame, lookback: int = 50, **_: object) -> dict[str, np.ndarray]:
    _ensure_ohlcv(df)
    lb = max(int(lookback), 2)
    high = df["high"].rolling(lb).max()
    low = df["low"].rolling(lb).min()
    diff = high - low
    close = df["close"]
    l618 = high - 0.618 * diff
    value = ((close - l618) / diff.replace(0, np.nan) * 100).fillna(0)
    return {
        "level_618": l618.to_numpy(dtype=float),
        "value": value.to_numpy(dtype=float),
    }


def fibonacci_extension(df: pd.DataFrame, lookback: int = 50, **_: object) -> dict[str, np.ndarray]:
    _ensure_ohlcv(df)
    lb = max(int(lookback), 2)
    high = df["high"].rolling(lb).max()
    low = df["low"].rolling(lb).min()
    diff = high - low
    close = df["close"]
    ext161 = high + 0.618 * diff
    value = ((close - ext161) / diff.replace(0, np.nan) * 100).fillna(0)
    return {
        "ext_161": ext161.to_numpy(dtype=float),
        "value": value.to_numpy(dtype=float),
    }


_CUSTOM = {
    "FIB_RETRACE": fibonacci_retrace,
    "FIB_EXT": fibonacci_extension,
}


def compute_custom(name: str, df: pd.DataFrame, **params: object) -> dict[str, np.ndarray]:
    fn = _CUSTOM.get(name.upper())
    if fn is None:
        raise KeyError(f"unknown custom indicator: {name}")
    return fn(df, **params)
