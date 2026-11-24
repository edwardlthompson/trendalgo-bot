"""Thread-safe LRU cache for Secret Sauce causal features and columnar masks."""

from __future__ import annotations

import threading
import zlib
from collections import OrderedDict
from collections.abc import Callable

import numpy as np
import pandas as pd

from trendalgo.ta.frame_prep import ohlcv_arrays
from trendalgo.ta.indicator_cache import signature_from_df

_MAX_CACHE = 64
_LOCK = threading.Lock()
_CACHE: OrderedDict[
    tuple[int, int, int, int], tuple[dict[str, np.ndarray], list[dict[str, float]]]
] = OrderedDict()


def _frame_key(df: pd.DataFrame) -> tuple[int, int, int, int]:
    sig = signature_from_df(df)
    if sig is not None:
        return (sig.bar_count, sig.first_ts, sig.last_ts, sig.price_tag)
    _, h, lo, c, v = ohlcv_arrays(df)
    n = len(df)
    if n == 0:
        return (0, 0, 0, 0)
    sample = np.array([c[0], c[-1], h[-1], lo[0], v[-1]], dtype=np.float64)
    return (n, 0, n, int(zlib.crc32(sample.tobytes())))


def get_cached_feature_matrix(
    df: pd.DataFrame,
    builder: Callable[[pd.DataFrame], list[dict[str, float]]],
) -> tuple[dict[str, np.ndarray], list[dict[str, float]]]:
    """Compute/cache ``(cols, feats)`` once per OHLCV frame across Secret Sauce stages."""
    if df is None or df.empty:
        return {}, []
    key = _frame_key(df)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit is not None:
            _CACHE.move_to_end(key)
            return hit
    feats = builder(df)
    if not feats:
        return {}, feats
    keys = list(feats[0].keys())
    cols: dict[str, np.ndarray] = {
        k: np.array([float(f.get(k) or 0.0) for f in feats], dtype=np.float64) for k in keys
    }
    entry = (cols, feats)
    with _LOCK:
        while len(_CACHE) >= _MAX_CACHE:
            _CACHE.popitem(last=False)
        _CACHE[key] = entry
    return entry
