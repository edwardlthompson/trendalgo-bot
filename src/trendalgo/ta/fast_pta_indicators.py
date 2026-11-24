"""Direct NumPy/Numba fast-paths for the 8 slowest pandas-ta-classic indicators."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.ta.frame_prep import ohlcv_arrays


def _sma_np(arr: np.ndarray, length: int) -> np.ndarray:
    n = len(arr)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < length or length <= 0:
        return out
    csum = np.empty(n + 1, dtype=np.float64)
    csum[0] = 0.0
    np.cumsum(arr, out=csum[1:])
    out[length - 1 :] = (csum[length:] - csum[:-length]) / float(length)
    return out


def _fast_psar(
    h: np.ndarray, lo: np.ndarray, c: np.ndarray, params: dict[str, Any]
) -> dict[str, np.ndarray]:
    from pandas_ta_classic.trend.psar import _psar_falling, _psar_loop  # noqa: PLC0415

    af = float(params.get("af") or 0.02)
    af0 = float(params.get("af0") or af)
    max_af = float(params.get("max_af") or 0.2)
    falling = bool(_psar_falling(pd.Series(h[:2]), pd.Series(lo[:2]))) if len(h) > 1 else False
    sar = float(c[0])
    ep = float(lo[1] if len(lo) > 1 else lo[0]) if falling else float(h[1] if len(h) > 1 else h[0])
    long_arr, short_arr, _, _ = _psar_loop(h, lo, len(h), falling, sar, ep, af0, max_af)
    combined = np.where(~np.isnan(long_arr), long_arr, short_arr)
    long_out = np.where(combined < c, combined, np.nan)
    short_out = np.where(combined >= c, combined, np.nan)
    return {"psarl": long_out, "psars": short_out, "value": combined}


def _fast_hilo(
    h: np.ndarray, lo: np.ndarray, c: np.ndarray, params: dict[str, Any]
) -> dict[str, np.ndarray]:
    from pandas_ta_classic.overlap.hilo import _hilo_loop  # noqa: PLC0415

    hl = int(params.get("high_length") or 13)
    ll = int(params.get("low_length") or 21)
    if len(c) < max(hl, ll):
        return {"value": np.full(len(c), np.nan, dtype=np.float64)}
    h_ma = _sma_np(h, hl)
    l_ma = _sma_np(lo, ll)
    hilo_arr, _, _ = _hilo_loop(c, h_ma, l_ma)
    return {"value": np.asarray(hilo_arr, dtype=np.float64)}


def _fast_hwc(c: np.ndarray, params: dict[str, Any]) -> dict[str, np.ndarray]:
    from pandas_ta_classic.volatility.hwc import _hwc_loop  # noqa: PLC0415

    na = float(params.get("na") or 0.2)
    nb = float(params.get("nb") or 0.1)
    nc = float(params.get("nc") or 0.1)
    nd = float(params.get("nd") or 0.1)
    scalar = float(params.get("scalar") or 1.0)
    res, _, _ = _hwc_loop(c, len(c), na, nb, nc, nd, scalar)
    return {"value": np.asarray(res, dtype=np.float64)}


def _fast_hwma(c: np.ndarray, params: dict[str, Any]) -> dict[str, np.ndarray]:
    from pandas_ta_classic.overlap.hwma import _hwma_loop  # noqa: PLC0415

    na = float(params.get("na") or 0.2)
    nb = float(params.get("nb") or 0.1)
    nc = float(params.get("nc") or 0.1)
    res = _hwma_loop(c, len(c), na, nb, nc)
    return {"value": np.asarray(res, dtype=np.float64)}


def _fast_lrsi(c: np.ndarray, params: dict[str, Any]) -> dict[str, np.ndarray]:
    from pandas_ta_classic.momentum.lrsi import _lrsi_loop  # noqa: PLC0415

    length = int(params.get("length") or 14)
    gamma = float(params.get("gamma") or 0.5)
    n = len(c)
    if n < length:
        return {"value": np.full(n, np.nan, dtype=np.float64)}
    l0, l1, l2, l3 = _lrsi_loop(c, n, gamma)
    cu = np.maximum(l0 - l1, 0.0) + np.maximum(l1 - l2, 0.0) + np.maximum(l2 - l3, 0.0)
    cd = np.maximum(l1 - l0, 0.0) + np.maximum(l2 - l1, 0.0) + np.maximum(l3 - l2, 0.0)
    denom = cu + cd
    denom = np.where(denom == 0.0, 1.0, denom)
    return {"value": np.asarray(100.0 * cu / denom, dtype=np.float64)}


def _fast_fisher(h: np.ndarray, lo: np.ndarray, params: dict[str, Any]) -> dict[str, np.ndarray]:
    from pandas_ta_classic.momentum.fisher import _fisher_loop  # noqa: PLC0415

    length = int(params.get("length") or 9)
    n = len(h)
    if n < max(length, 1):
        return {"value": np.full(n, np.nan, dtype=np.float64)}
    hl2_s = pd.Series(0.5 * (h + lo))
    hi = hl2_s.rolling(length).max().to_numpy(dtype=np.float64)
    lo_r = hl2_s.rolling(length).min().to_numpy(dtype=np.float64)
    hlr = np.maximum(hi - lo_r, 0.001)
    pos = (hl2_s.to_numpy(dtype=np.float64) - lo_r) / hlr - 0.5
    fisher_arr = _fisher_loop(pos, n, length)
    return {"value": np.asarray(fisher_arr, dtype=np.float64)}


def _fast_jma(c: np.ndarray, params: dict[str, Any]) -> dict[str, np.ndarray]:
    from pandas_ta_classic.overlap.jma import _jma_loop, _jma_phase_ratio  # noqa: PLC0415

    raw_len = int(params.get("length") or 7)
    phase = float(params.get("phase") or 0.0)
    if len(c) < raw_len:
        return {"value": np.full(len(c), np.nan, dtype=np.float64)}
    half = 0.5 * (raw_len - 1)
    pr = _jma_phase_ratio(phase)
    l1 = max((np.log(np.sqrt(half)) / np.log(2.0)) + 2.0, 0.0)
    pow1 = max(l1 - 2.0, 0.5)
    l2 = l1 * np.sqrt(half)
    bet = l2 / (l2 + 1.0)
    beta = 0.45 * (raw_len - 1) / (0.45 * (raw_len - 1) + 2.0)
    out = np.asarray(_jma_loop(c, l1, pow1, bet, beta, pr, 10), dtype=np.float64)
    out[0 : raw_len - 1] = np.nan
    return {"value": out}


def compute_fast_pta(
    upper: str, df: pd.DataFrame, params: dict[str, Any]
) -> dict[str, np.ndarray] | None:
    """Return fast NumPy/Numba output for supported slow indicators, else None."""
    if params.get("offset") or params.get("mamode") or params.get("talib") is True:
        return None
    if any(k in params for k in ("fillna", "fill_method", "channel_eval", "drift")):
        return None
    _, h, lo, c, _ = ohlcv_arrays(df)
    if upper == "PSAR":
        return _fast_psar(h, lo, c, params)
    if upper == "HILO":
        return _fast_hilo(h, lo, c, params)
    if upper == "HWC":
        return _fast_hwc(c, params)
    if upper == "HWMA":
        return _fast_hwma(c, params)
    if upper == "LRSI":
        return _fast_lrsi(c, params)
    if upper == "FISHER":
        return _fast_fisher(h, lo, params)
    if upper == "JMA":
        return _fast_jma(c, params)
    if upper == "QQE":
        from trendalgo.ta.fast_pta_qqe import fast_qqe  # noqa: PLC0415

        return fast_qqe(c, params)
    return None
