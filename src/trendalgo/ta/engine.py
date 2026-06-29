"""TA compute layer — TA-Lib C API when installed, pandas fallbacks otherwise."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd

from trendalgo.strategies.runtime.indicators import close_series, ema, macd, rsi, sma
from trendalgo.ta.custom_indicators import compute_custom
from trendalgo.ta.extended_catalog import CUSTOM_TA_NAMES
from trendalgo.ta.indicator_cache import get_indicator_cache, signature_from_df
from trendalgo.ta.pandas_ta_catalog import is_pandas_ta_indicator, pandas_ta_available
from trendalgo.ta.pandas_ta_engine import compute_pandas_ta

_OHLCV = ("open", "high", "low", "close", "volume")


def talib_available() -> bool:
    try:
        import talib  # noqa: F401

        return True
    except ImportError:
        return False


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in _OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"missing OHLCV columns: {missing}")
    return df


def _arr(df: pd.DataFrame, col: str) -> np.ndarray:
    return cast(np.ndarray, df[col].to_numpy(dtype=float))


def compute_talib(name: str, df: pd.DataFrame, **params: Any) -> dict[str, np.ndarray]:
    """Call TA-Lib function by name (https://ta-lib.org/api/)."""
    import talib

    _ensure_ohlcv(df)
    fn = getattr(talib, name, None)
    if fn is None:
        raise KeyError(f"unknown TA-Lib function: {name}")
    o, h, lo, c, v = (_arr(df, x) for x in _OHLCV)
    upper = name.upper()
    if upper.startswith("CDL"):
        return {"pattern": np.asarray(fn(o, h, lo, c), dtype=float)}
    if upper == "MACD":
        macd_line, signal, hist = fn(c, **params)
        return {"macd": macd_line, "signal": signal, "hist": hist}
    if upper in {"MACDEXT", "MACDFIX"}:
        macd_line, signal, hist = fn(c)
        return {"macd": macd_line, "signal": signal, "hist": hist}
    if upper == "BBANDS":
        upper_b, mid, lower_b = fn(c, **params)
        return {"upper": upper_b, "middle": mid, "lower": lower_b}
    if upper == "STOCH":
        slowk, slowd = fn(h, lo, c, **params)
        return {"slowk": slowk, "slowd": slowd}
    if upper == "STOCHF":
        fastk, fastd = fn(h, lo, c, **params)
        return {"fastk": fastk, "fastd": fastd}
    if upper == "STOCHRSI":
        fastk, fastd = fn(c, **params)
        return {"fastk": fastk, "fastd": fastd}
    if upper == "AROON":
        down, up = fn(h, lo, **params)
        return {"down": down, "up": up}
    if upper == "AROONOSC":
        return {"value": fn(h, lo, **params)}
    if upper == "MINMAX":
        mn, mx = fn(c, **params)
        return {"min": mn, "max": mx, "value": mn}
    if upper == "MINMAXINDEX":
        mn_idx, mx_idx = fn(c, **params)
        return {"minidx": mn_idx, "maxidx": mx_idx, "value": mn_idx.astype(float)}
    if upper in {"SAR", "SAREXT"}:
        return {"value": fn(h, lo, **params)}
    if upper == "BOP":
        return {"value": fn(o, h, lo, c)}
    if upper == "MEDPRICE":
        return {"value": fn(h, lo)}
    if upper == "TYPPRICE":
        return {"value": fn(h, lo, c)}
    if upper == "WCLPRICE":
        return {"value": fn(h, lo, c)}
    if upper == "TRANGE":
        return {"value": fn(h, lo, c)}
    if upper == "MAMA":
        mama, fama = fn(c, **params)
        return {"mama": mama, "fama": fama, "value": mama}
    if upper == "HT_PHASOR":
        inphase, quadrature = fn(c)
        return {"inphase": inphase, "quadrature": quadrature, "value": inphase}
    if upper == "HT_SINE":
        sine, leadsine = fn(c)
        return {"sine": sine, "leadsine": leadsine, "value": sine}
    if upper in {"HT_DCPERIOD", "HT_DCPHASE", "HT_TRENDMODE"}:
        return {"value": fn(c)}
    if upper in {"PLUS_DI", "MINUS_DI", "ADX", "ADXR", "DX", "ATR", "NATR"}:
        return {"value": fn(h, lo, c, **params)}
    if upper == "MFI":
        return {"value": fn(h, lo, c, v, **params)}
    if upper in {"AD", "ADOSC"}:
        return {"value": fn(h, lo, c, v, **params)}
    if upper == "OBV":
        return {"value": fn(c, v)}
    if upper in {"AVGPRICE", "MEDPRICE", "TYPPRICE", "WCLPRICE"}:
        if upper == "AVGPRICE":
            return {"value": fn(o, h, lo, c)}
        if upper == "MEDPRICE":
            return {"value": fn(h, lo)}
        if upper == "TYPPRICE":
            return {"value": fn(h, lo, c)}
        return {"value": fn(h, lo, c)}
    if upper == "MIDPRICE":
        return {"value": fn(h, lo, **params)}
    if upper in {"WILLR", "CCI", "ULTOSC"}:
        clean = {k: v for k, v in params.items() if k != "timeperiod"}
        return {"value": fn(h, lo, c, **clean)}
    if upper in {"PLUS_DM", "MINUS_DM"}:
        return {"value": fn(h, lo, **params)}
    if upper in {"BETA", "CORREL"}:
        return {"value": fn(c, c, **params)}
    return {"value": fn(c, **params)}


def compute_pandas(name: str, df: pd.DataFrame, **params: Any) -> dict[str, np.ndarray]:
    """Pandas fallbacks for common indicators when TA-Lib is not installed."""
    _ensure_ohlcv(df)
    c = close_series(df)
    upper = name.upper()
    if upper == "EMA":
        period = int(params.get("timeperiod", 14))
        return {"value": ema(c, period).to_numpy(dtype=float)}
    if upper == "SMA":
        period = int(params.get("timeperiod", 14))
        return {"value": sma(c, period).to_numpy(dtype=float)}
    if upper == "RSI":
        period = int(params.get("timeperiod", 14))
        return {"value": rsi(c, period).to_numpy(dtype=float)}
    if upper == "MACD":
        m, sig, hist = macd(
            c,
            fastperiod=int(params.get("fastperiod", 12)),
            slowperiod=int(params.get("slowperiod", 26)),
            signalperiod=int(params.get("signalperiod", 9)),
        )
        return {
            "macd": m.to_numpy(dtype=float),
            "signal": sig.to_numpy(dtype=float),
            "hist": hist.to_numpy(dtype=float),
        }
    if upper == "ROC":
        period = int(params.get("timeperiod", 10))
        prev = c.shift(period)
        roc = ((c / prev) - 1) * 100
        return {"value": roc.to_numpy(dtype=float)}
    if upper == "MOM":
        period = int(params.get("timeperiod", 10))
        return {"value": (c - c.shift(period)).to_numpy(dtype=float)}
    raise KeyError(f"no pandas fallback for {name}")


def _compute_uncached(name: str, df: pd.DataFrame, **params: Any) -> dict[str, np.ndarray]:
    upper = name.upper()
    if upper in CUSTOM_TA_NAMES:
        return compute_custom(upper, df, **params)
    if talib_available() and upper.startswith("CDL") is False:
        try:
            from trendalgo.ta.catalog import TA_FUNCTION_NAMES

            if upper in TA_FUNCTION_NAMES:
                return compute_talib(name, df, **params)
        except (KeyError, TypeError, ValueError):
            pass
    if is_pandas_ta_indicator(upper) and pandas_ta_available():
        try:
            return compute_pandas_ta(upper, df, **params)
        except (KeyError, TypeError, ValueError):
            pass
    if talib_available():
        try:
            return compute_talib(name, df, **params)
        except (KeyError, TypeError, ValueError):
            pass
    return compute_pandas(name, df, **params)


def compute(name: str, df: pd.DataFrame, **params: Any) -> dict[str, np.ndarray]:
    sig = signature_from_df(df)
    if sig is not None:
        cached = get_indicator_cache().get(name, sig, params)
        if cached is not None:
            return cached
    result = _compute_uncached(name, df, **params)
    if sig is not None:
        get_indicator_cache().put(name, sig, params, result)
    return result
