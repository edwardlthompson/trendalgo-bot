"""U — adversarial veto: skip entries that historically look like false starts."""

from __future__ import annotations

import numpy as np
import pandas as pd


def false_entry_veto_mask(
    df: pd.DataFrame, entries: np.ndarray, *, look_ahead: int = 3
) -> np.ndarray:
    """Veto entry bars where close falls over next look_ahead bars (in-sample autopsy).

    Used only as a soft AND on helper entries after fee search — not as live lookahead.
    For live, the same *feature pattern* at entry (e.g. rsi high + below_sma20) should be used;
    this helper returns a training mask for residual analysis / Study honesty.
    """
    close = df["close"].to_numpy(dtype=float)
    n = len(close)
    veto = np.zeros(n, dtype=bool)
    idxs = np.flatnonzero(entries)
    for i in idxs:
        j = min(n - 1, int(i) + look_ahead)
        if j > i and close[j] < close[i] * 0.99:
            veto[i] = True
    return veto


def apply_veto(entries: np.ndarray, veto: np.ndarray) -> np.ndarray:
    out = np.asarray(entries, dtype=bool) & ~np.asarray(veto, dtype=bool)
    return np.asarray(out, dtype=bool)
