"""Fast NumPy/Numba path for QQE (Quantitative Qualitative Estimation)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def fast_qqe(c: np.ndarray, params: dict[str, Any]) -> dict[str, np.ndarray]:
    """Compute QQE using pandas-ta-classic's exact RSI/EMA + compiled _qqe_loop."""
    from pandas_ta_classic.momentum.qqe import _qqe_loop  # noqa: PLC0415
    from pandas_ta_classic.momentum.rsi import rsi as pta_rsi  # noqa: PLC0415
    from pandas_ta_classic.overlap.ema import ema as pta_ema  # noqa: PLC0415

    length = int(params.get("length") or 14)
    smooth = int(params.get("smooth") or 5)
    factor = float(params.get("factor") or 4.236)
    wilders_length = 2 * length - 1
    if len(c) < max(length, smooth, wilders_length):
        return {"value": np.full(len(c), np.nan, dtype=np.float64)}
    c_s = pd.Series(c)
    rsi_s = pta_rsi(c_s, length=length)
    if rsi_s is None:
        return {"value": np.full(len(c), np.nan, dtype=np.float64)}
    rsi_ma = pta_ema(rsi_s, length=smooth)
    if rsi_ma is None:
        return {"value": np.full(len(c), np.nan, dtype=np.float64)}
    tr = rsi_ma.diff(1).abs()
    sm_tr = pta_ema(tr, length=wilders_length)
    dar_ema = pta_ema(sm_tr, length=wilders_length) if sm_tr is not None else None
    if dar_ema is None:
        return {"value": np.full(len(c), np.nan, dtype=np.float64)}
    dar = factor * dar_ema
    ub = (rsi_ma + dar).to_numpy(dtype=np.float64)
    lb = (rsi_ma - dar).to_numpy(dtype=np.float64)
    rm = rsi_ma.to_numpy(dtype=np.float64)
    _, _, _, qqe_arr, _, _ = _qqe_loop(rm, ub, lb, len(c))
    return {"value": np.asarray(qqe_arr, dtype=np.float64), "rsi_ma": rm}
