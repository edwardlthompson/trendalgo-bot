"""Compute layer for pandas-ta-classic indicators."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd

from trendalgo.ta.frame_cache import ATTR_READONLY
from trendalgo.ta.pandas_ta_catalog import id_to_pandas_ta_slug, is_pandas_ta_indicator


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    need = ("open", "high", "low", "close", "volume")
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"missing OHLCV columns: {missing}")
    return df


def _series_to_array(value: Any) -> np.ndarray:
    if isinstance(value, pd.Series):
        return cast(np.ndarray, value.to_numpy(dtype=float))
    if isinstance(value, pd.DataFrame):
        return cast(np.ndarray, value.iloc[:, 0].to_numpy(dtype=float))
    return np.asarray(value, dtype=float)


def _normalize_result(result: Any, *, length: int | None = None) -> dict[str, np.ndarray]:
    if result is None:
        raise ValueError("pandas-ta returned no data")
    if isinstance(result, pd.Series):
        return _pad_to_length({"value": _series_to_array(result)}, length)
    if isinstance(result, pd.DataFrame):
        out: dict[str, np.ndarray] = {}
        for col in result.columns:
            key = str(col).lower().replace(" ", "_")
            out[key] = _series_to_array(result[col])
        if "value" not in out:
            for prefer in ("supert_", "superts", "macd", "middle", "close"):
                for key, arr in out.items():
                    if prefer in key:
                        out["value"] = arr
                        break
                if "value" in out:
                    break
            if "value" not in out and out:
                out["value"] = next(iter(out.values()))
        return _pad_to_length(out, length)
    if isinstance(result, tuple):
        keys = ("value", "signal", "hist", "lower", "middle", "upper")
        out = {}
        for idx, item in enumerate(result):
            out[keys[idx] if idx < len(keys) else f"col_{idx}"] = _series_to_array(item)
        return _pad_to_length(out, length)
    out = {"value": _series_to_array(result)}
    return _pad_to_length(out, length)


def _pad_to_length(out: dict[str, np.ndarray], length: int | None) -> dict[str, np.ndarray]:
    if length is None:
        return out
    padded: dict[str, np.ndarray] = {}
    for key, arr in out.items():
        if len(arr) == length:
            padded[key] = arr
            continue
        if len(arr) == 0:
            padded[key] = np.full(length, np.nan, dtype=float)
            continue
        series = pd.Series(arr)
        expanded = series.reindex(range(length), method="ffill").to_numpy(dtype=float)
        padded[key] = expanded
    if "value" not in padded and padded:
        padded["value"] = next(iter(padded.values()))
    return padded


def compute_pandas_ta(name: str, df: pd.DataFrame, **params: Any) -> dict[str, np.ndarray]:
    if not is_pandas_ta_indicator(name):
        raise KeyError(f"not a pandas-ta-classic indicator: {name}")
    _ensure_ohlcv(df)
    slug = id_to_pandas_ta_slug(name)
    if df.attrs.get(ATTR_READONLY) and isinstance(df.index, pd.DatetimeIndex):
        work = df
    else:
        work = df.copy()
        if not isinstance(work.index, pd.DatetimeIndex) and "timestamp_ms" in work.columns:
            work.index = pd.to_datetime(work["timestamp_ms"], unit="ms", utc=True)
    accessor = getattr(work.ta, slug, None)
    if accessor is None:
        raise KeyError(f"pandas-ta-classic missing indicator: {slug}")
    clean = {k: v for k, v in params.items() if v is not None}
    result = accessor(**clean)
    return _normalize_result(result, length=len(work))
