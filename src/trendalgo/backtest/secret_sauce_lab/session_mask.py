"""N — soft session/hour allowlist with holdout check."""

from __future__ import annotations

import numpy as np
import pandas as pd


def hour_allow_mask(df: pd.DataFrame, *, allowed_hours: set[int] | None = None) -> np.ndarray:
    """True on bars whose UTC hour is in allowed_hours (default: 8–20 UTC)."""
    hours = allowed_hours if allowed_hours is not None else set(range(8, 21))
    if not isinstance(df.index, pd.DatetimeIndex):
        return np.ones(len(df), dtype=bool)
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    return np.array([int(ts.hour) in hours for ts in idx], dtype=bool)


def apply_session_to_entries(entries: np.ndarray, df: pd.DataFrame) -> np.ndarray:
    out = np.asarray(entries, dtype=bool) & hour_allow_mask(df)
    return np.asarray(out, dtype=bool)
