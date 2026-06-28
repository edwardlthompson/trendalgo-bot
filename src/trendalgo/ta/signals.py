"""Universal signal generation for TA strategies on OHLCV data."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.ta.catalog import TA_FUNCTION_NAMES
from trendalgo.ta.engine import compute
from trendalgo.ta.extended_catalog import CUSTOM_TA_NAMES
from trendalgo.ta.pandas_ta_catalog import is_pandas_ta_indicator

# Strategies where close crossing the indicator line drives entries/exits.
PRICE_CROSS_IDS: frozenset[str] = frozenset(
    {
        *{
            n
            for n in (
                "SMA",
                "EMA",
                "DEMA",
                "TEMA",
                "WMA",
                "KAMA",
                "T3",
                "TRIMA",
                "BBANDS",
                "MIDPOINT",
                "MIDPRICE",
                "HT_TRENDLINE",
                "SAR",
                "SAREXT",
                "FIB_RETRACE",
                "FIB_EXT",
            )
        },
        *{
            n.upper()
            for n in (
                "SUPERTREND",
                "VWAP",
                "VWMA",
                "HMA",
                "ZLMA",
                "ALMA",
                "FWMA",
                "PWMA",
                "SWMA",
                "SINWMA",
                "HWMA",
                "VIDYA",
                "RMA",
                "JMA",
                "DONCHIAN",
                "KC",
                "ACCBANDS",
                "HILO",
                "HWC",
                "ICHIMOKU",
                "PSAR",
                "HL2",
                "HLC3",
                "OHLC4",
                "WCP",
                "AVGPRICE",
                "MEDPRICE",
                "TYPPRICE",
                "WCLPRICE",
            )
        },
    }
)

# Oscillators typically bounded ~0-100 — use threshold reversal backtest.
BOUNDED_OSC_IDS: frozenset[str] = frozenset(
    {
        *{
            n
            for n in (
                "RSI",
                "MFI",
                "CMO",
                "CCI",
                "WILLR",
                "STOCHRSI",
                "ADX",
                "ADXR",
                "DX",
                "ULTOSC",
                "AROON",
                "AROONOSC",
                "BOP",
            )
        },
        *{
            n.upper()
            for n in (
                "STOCH",
                "STOCHF",
                "KDJ",
                "QQE",
                "RSX",
                "LRSI",
                "TSI",
                "FISHER",
                "CTI",
                "CFO",
                "CG",
                "ER",
                "INERTIA",
                "PGO",
                "PSL",
                "RVI",
                "RVGI",
                "SMI",
                "STC",
                "TD_SEQ",
                "UO",
                "VHF",
                "VORTEX",
                "WTO",
                "SLOPE",
            )
        },
    }
)

MACD_IDS: frozenset[str] = frozenset({"MACD", "MACDEXT", "MACDFIX"})
MACD_LIKE_IDS: frozenset[str] = frozenset({"MACD", "MACDEXT", "MACDFIX", "PVO", "VWMACD"})
STOCH_IDS: frozenset[str] = frozenset({"STOCH", "STOCHF"})
ZERO_CROSS_IDS: frozenset[str] = frozenset(
    {
        "APO",
        "PPO",
        "ROC",
        "MOM",
        "ROCP",
        "ROCR",
        "ROCR100",
        "AO",
        "COPPOCK",
        "KST",
        "EOM",
        "EFI",
        "CMF",
        "VFI",
        "PVI",
        "NVI",
        "SQUEEZE",
        "SQUEEZE_PRO",
        "VORTEX",
    }
)
MA_CROSS_IDS: frozenset[str] = frozenset({"SMA", "EMA", "DEMA", "TEMA", "WMA", "KAMA", "T3", "TRIMA", "HMA", "VWMA"})
TALIB_NO_PERIOD: frozenset[str] = frozenset(
    {
        "APO",
        "PPO",
        "AD",
        "ADOSC",
        "OBV",
        "BOP",
        "TRANGE",
        "HT_DCPERIOD",
        "HT_DCPHASE",
        "HT_PHASOR",
        "HT_SINE",
        "HT_TRENDMODE",
        "MAMA",
        "SAR",
        "SAREXT",
        "ULTOSC",
        "AVGPRICE",
        "MEDPRICE",
        "TYPPRICE",
        "WCLPRICE",
        "MIDPRICE",
    }
)


def _pta_params(params: dict[str, Any]) -> dict[str, Any]:
    out = dict(params)
    if "timeperiod" in out and "length" not in out:
        out["length"] = int(out.pop("timeperiod"))
    if "fastperiod" in out and "fast" not in out:
        out["fast"] = int(out.pop("fastperiod"))
    if "slowperiod" in out and "slow" not in out:
        out["slow"] = int(out.pop("slowperiod"))
    return out


def primary_series(strategy_id: str, out: dict[str, np.ndarray], close: pd.Series) -> pd.Series:
    upper = strategy_id.upper()
    if "value" in out:
        return pd.Series(out["value"], index=close.index)
    if upper in MACD_IDS and "macd" in out:
        return pd.Series(out["macd"], index=close.index)
    if upper in {"BBANDS", "KC", "ACCBANDS", "DONCHIAN"} and "middle" in out:
        return pd.Series(out["middle"], index=close.index)
    if upper == "SUPERTREND":
        for key, arr in out.items():
            if str(key).lower().startswith("supert_") or str(key).lower().startswith("superts"):
                return pd.Series(arr, index=close.index)
    if upper == "ICHIMOKU" and "kijun" in out:
        return pd.Series(out["kijun"], index=close.index)
    if "hist" in out:
        return pd.Series(out["hist"], index=close.index)
    if "pattern" in out:
        return pd.Series(out["pattern"], index=close.index)
    first_key = next(iter(out))
    return pd.Series(out[first_key], index=close.index)


def _signal_series(out: dict[str, np.ndarray], close: pd.Series) -> pd.Series:
    for key in ("signal", "pvos", "vwmacds", "slowd", "fastd", "fama"):
        if key in out:
            return pd.Series(out[key], index=close.index)
    primary = primary_series("", out, close)
    return primary * 0.0


def signal_kind(strategy_id: str) -> str:
    upper = strategy_id.upper()
    if upper.startswith("CDL"):
        return "cdl_pattern"
    if upper in MACD_LIKE_IDS:
        return "macd_cross"
    if upper in STOCH_IDS:
        return "stoch_cross"
    if upper in MA_CROSS_IDS:
        return "ma_cross"
    if upper in PRICE_CROSS_IDS or upper in {"MAMA"}:
        return "price_cross"
    if upper in BOUNDED_OSC_IDS:
        return "bounded_reversal"
    if upper in ZERO_CROSS_IDS or upper in CUSTOM_TA_NAMES or is_pandas_ta_indicator(upper):
        return "zero_cross"
    if upper in {"AD", "ADOSC", "OBV", "BOP", "TRANGE", "AROONOSC", "MINMAX", "MINMAXINDEX"}:
        return "zero_cross"
    if upper in {"HT_DCPERIOD", "HT_DCPHASE", "HT_PHASOR", "HT_SINE", "HT_TRENDMODE"}:
        return "zero_cross"
    if upper in TA_FUNCTION_NAMES:
        return "bounded_reversal"
    return "zero_cross"


def resolve_preset(strategy_id: str, ta_params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = _pta_params(ta_params or {})
    upper = strategy_id.upper()
    kind = signal_kind(upper)
    preset: dict[str, Any] = {"fn": upper, "kind": kind, **params}
    if kind == "ma_cross":
        preset.setdefault("fast", int(params.get("fast", 10)))
        preset.setdefault("slow", int(params.get("slow", 30)))
    if kind in {"bounded_reversal", "zero_cross"}:
        preset.setdefault("timeperiod", int(params.get("timeperiod", params.get("length", 14))))
    if kind == "bounded_reversal":
        preset.setdefault("entry_level", 30.0)
        preset.setdefault("exit_level", 70.0)
    return preset


def _compute_kwargs(fn: str, params: dict[str, Any], *, period: int | None = None) -> dict[str, Any]:
    """Build kwargs for compute() without duplicate length/timeperiod."""
    out = dict(params)
    out.pop("timeperiod", None)
    out.pop("length", None)
    if period is not None:
        upper = fn.upper()
        if upper in TALIB_NO_PERIOD:
            pass
        elif is_pandas_ta_indicator(upper) or upper in CUSTOM_TA_NAMES:
            out["length"] = period
        else:
            out["timeperiod"] = period
    return out


def _bool_cross_up(a: pd.Series, b: pd.Series) -> np.ndarray:
    a_v = a.to_numpy(dtype=float)
    b_v = b.to_numpy(dtype=float)
    return _bool_cross_up_arr(a_v, b_v)


def _bool_cross_down(a: pd.Series, b: pd.Series) -> np.ndarray:
    a_v = a.to_numpy(dtype=float)
    b_v = b.to_numpy(dtype=float)
    return _bool_cross_down_arr(a_v, b_v)


def _bool_cross_up_arr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    prev_a = np.roll(a, 1)
    prev_b = np.roll(b, 1)
    prev_a[0] = a[0]
    prev_b[0] = b[0]
    return (prev_a <= prev_b) & (a > b)


def _bool_cross_down_arr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    prev_a = np.roll(a, 1)
    prev_b = np.roll(b, 1)
    prev_a[0] = a[0]
    prev_b[0] = b[0]
    return (prev_a >= prev_b) & (a < b)


def signals_for_preset(df: pd.DataFrame, preset: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    kind = preset["kind"]
    fn = preset["fn"]
    params = _pta_params({k: v for k, v in preset.items() if k not in {"fn", "kind", "entry_level", "exit_level"}})
    close = df["close"]
    n = len(df)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    if kind == "macd_cross":
        out = compute(fn, df, **params)
        m = primary_series(fn, out, close)
        s = _signal_series(out, close)
        entries = _bool_cross_up(m, s)
        exits = _bool_cross_down(m, s)
    elif kind == "stoch_cross":
        out = compute(fn, df, **params)
        k = pd.Series(out.get("slowk", out.get("fastk", out.get("value"))), index=close.index)
        d = pd.Series(out.get("slowd", out.get("fastd", k)), index=close.index)
        entries = _bool_cross_up(k, d)
        exits = _bool_cross_down(k, d)
    elif kind == "ma_cross":
        fast = int(preset.get("fast", 10))
        slow = int(preset.get("slow", 30))
        slow_ma = primary_series(fn, compute(fn, df, **_compute_kwargs(fn, {}, period=slow)), close)
        fast_ma = primary_series(fn, compute(fn, df, **_compute_kwargs(fn, {}, period=fast)), close)
        entries = _bool_cross_up(fast_ma, slow_ma)
        exits = _bool_cross_down(fast_ma, slow_ma)
    elif kind == "price_cross":
        out = compute(fn, df, **params)
        line = primary_series(fn, out, close)
        entries = _bool_cross_up(close, line)
        exits = _bool_cross_down(close, line)
    elif kind == "bounded_reversal":
        period = int(preset.get("timeperiod", preset.get("length", 14)))
        entry_level = float(preset.get("entry_level", 30))
        exit_level = float(preset.get("exit_level", 70))
        out = compute(fn, df, **_compute_kwargs(fn, params, period=period))
        r = primary_series(fn, out, close)
        entries = ((r.shift(1) < entry_level) & (r >= entry_level)).fillna(False).to_numpy(dtype=bool)
        exits = ((r.shift(1) > exit_level) & (r <= exit_level)).fillna(False).to_numpy(dtype=bool)
    elif kind == "cdl_pattern":
        out = compute(fn, df, **params)
        p = primary_series(fn, out, close)
        entries = ((p.shift(1) <= 0) & (p > 0)).fillna(False).to_numpy(dtype=bool)
        exits = ((p.shift(1) >= 0) & (p < 0)).fillna(False).to_numpy(dtype=bool)
    else:  # zero_cross default
        period = int(preset.get("timeperiod", preset.get("length", 14)))
        out = compute(fn, df, **_compute_kwargs(fn, params, period=period))
        v = primary_series(fn, out, close)
        entries = ((v.shift(1) <= 0) & (v > 0)).fillna(False).to_numpy(dtype=bool)
        exits = ((v.shift(1) >= 0) & (v < 0)).fillna(False).to_numpy(dtype=bool)
    return entries, exits
