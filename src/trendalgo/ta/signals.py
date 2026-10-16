"""Universal signal generation for TA strategies on OHLCV data."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.strategies.runtime.indicators import close_series
from trendalgo.ta.engine import compute
from trendalgo.ta.extended_catalog import CUSTOM_TA_NAMES
from trendalgo.ta.pandas_ta_catalog import is_pandas_ta_indicator
from trendalgo.ta.signal_kinds import (
    BOUNDED_OSC_IDS,
    DI_CROSS_IDS,
    MA_CROSS_IDS,
    MACD_IDS,
    MACD_LIKE_IDS,
    MATH_SKIP_IDS,
    PRICE_CROSS_IDS,
    STOCH_IDS,
    ZERO_CROSS_IDS,
    apply_kind_defaults,
    signal_kind,
)

__all__ = [
    "BOUNDED_OSC_IDS",
    "DI_CROSS_IDS",
    "MACD_IDS",
    "MACD_LIKE_IDS",
    "MATH_SKIP_IDS",
    "MA_CROSS_IDS",
    "PRICE_CROSS_IDS",
    "STOCH_IDS",
    "ZERO_CROSS_IDS",
    "primary_series",
    "resolve_preset",
    "signal_kind",
    "signals_for_preset",
]

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
        "HT_TRENDLINE",
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
# Strip bogus default timeperiod; these use dedicated kwargs.
TALIB_STRIP_TIMEPERIOD: frozenset[str] = frozenset(
    {*TALIB_NO_PERIOD, "STOCH", "STOCHF", "STOCHRSI", "MACD", "MACDEXT", "MACDFIX"}
)


def _pta_params(params: dict[str, Any]) -> dict[str, Any]:
    """Rename TA-Lib-style kwargs to pandas-ta names. Do not use for TA-Lib compute."""
    out = dict(params)
    if "timeperiod" in out and "length" not in out:
        out["length"] = int(out.pop("timeperiod"))
    if "fastperiod" in out and "fast" not in out:
        out["fast"] = int(out.pop("fastperiod"))
    if "slowperiod" in out and "slow" not in out:
        out["slow"] = int(out.pop("slowperiod"))
    return out


def _compute_params(strategy_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Params for compute(): pandas-ta gets length/fast/slow; TA-Lib keeps timeperiod."""
    upper = strategy_id.upper()
    if is_pandas_ta_indicator(upper) or upper in CUSTOM_TA_NAMES:
        return _sanitize_compute_kwargs(upper, _pta_params(params))
    return _sanitize_compute_kwargs(upper, dict(params))


def _sanitize_compute_kwargs(strategy_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Drop kwargs TA-Lib rejects (e.g. default timeperiod on SAR/MAMA/STOCHF)."""
    upper = strategy_id.upper()
    out = dict(params)
    if upper in TALIB_STRIP_TIMEPERIOD:
        out.pop("timeperiod", None)
        out.pop("length", None)
    if upper == "SAR":
        out.setdefault("acceleration", 0.02)
        out.setdefault("maximum", 0.2)
    if upper == "STOCHF":
        out.setdefault("fastk_period", 5)
        out.setdefault("fastd_period", 3)
        out.setdefault("fastd_matype", 0)
    if upper == "STOCH":
        out.setdefault("fastk_period", 5)
        out.setdefault("slowk_period", 3)
        out.setdefault("slowd_period", 3)
    if upper == "MAMA":
        out.setdefault("fastlimit", 0.5)
        out.setdefault("slowlimit", 0.05)
    return out


def primary_series(strategy_id: str, out: dict[str, np.ndarray], close: pd.Series) -> pd.Series:
    upper = strategy_id.upper()
    # Bands / channels: middle line (Investopedia BBANDS mid = SMA), never lower "value".
    if upper in {"BBANDS", "KC", "ACCBANDS", "DONCHIAN"}:
        if "middle" in out:
            return pd.Series(out["middle"], index=close.index)
        for key, arr in out.items():
            kl = str(key).lower()
            if "mid" in kl or kl.startswith("dcm"):
                return pd.Series(arr, index=close.index)
    if upper in MACD_IDS and "macd" in out:
        return pd.Series(out["macd"], index=close.index)
    if upper == "MAMA" and "mama" in out:
        return pd.Series(out["mama"], index=close.index)
    if upper == "SUPERTREND":
        for key, arr in out.items():
            if str(key).lower().startswith("supert_") or str(key).lower().startswith("superts"):
                return pd.Series(arr, index=close.index)
    if upper == "ICHIMOKU" and "kijun" in out:
        return pd.Series(out["kijun"], index=close.index)
    if upper == "PSAR":
        # pandas-ta splits long/short SAR; combine so close can cross either side (Investopedia flip).
        long_arr = short_arr = None
        for key, arr in out.items():
            kl = str(key).lower()
            if "psarl" in kl:
                long_arr = np.asarray(arr, dtype=float)
            elif "psars" in kl:
                short_arr = np.asarray(arr, dtype=float)
        if long_arr is not None and short_arr is not None:
            combined = np.where(np.isfinite(long_arr), long_arr, short_arr)
            return pd.Series(combined, index=close.index)
        if "value" in out:
            return pd.Series(out["value"], index=close.index)
    if "value" in out:
        return pd.Series(out["value"], index=close.index)
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


def resolve_preset(strategy_id: str, ta_params: dict[str, Any] | None = None) -> dict[str, Any]:
    upper = strategy_id.upper()
    params = _compute_params(upper, ta_params or {})
    kind = signal_kind(upper)
    preset: dict[str, Any] = {"fn": upper, "kind": kind, **params}
    return apply_kind_defaults(preset, kind=kind, upper=upper)


def _compute_kwargs(
    fn: str, params: dict[str, Any], *, period: int | None = None
) -> dict[str, Any]:
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
    return _bool_cross_up_arr(a.to_numpy(dtype=float), b.to_numpy(dtype=float))


def _bool_cross_down(a: pd.Series, b: pd.Series) -> np.ndarray:
    return _bool_cross_down_arr(a.to_numpy(dtype=float), b.to_numpy(dtype=float))


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
    fn = str(preset["fn"])
    raw = {k: v for k, v in preset.items() if k not in {"fn", "kind", "entry_level", "exit_level"}}
    params = _compute_params(fn, raw)
    close = close_series(df)
    n = len(df)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    if kind == "math_skip":
        return entries, exits
    if kind == "di_cross":
        # Investopedia Wilder DMI: long when +DI crosses above −DI.
        period = int(preset.get("timeperiod", preset.get("length", 14)))
        plus = primary_series(
            "PLUS_DI",
            compute("PLUS_DI", df, **_compute_kwargs("PLUS_DI", {}, period=period)),
            close,
        )
        minus = primary_series(
            "MINUS_DI",
            compute("MINUS_DI", df, **_compute_kwargs("MINUS_DI", {}, period=period)),
            close,
        )
        entries = _bool_cross_up(plus, minus)
        exits = _bool_cross_down(plus, minus)
    elif kind == "macd_cross":
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
        entries = (
            ((r.shift(1) < entry_level) & (r >= entry_level)).fillna(False).to_numpy(dtype=bool)
        )
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
