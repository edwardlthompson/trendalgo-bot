"""Pre-extract contiguous OHLCV float64 arrays and stamp cache signatures."""

from __future__ import annotations

import threading
import zlib
from collections import OrderedDict

import numpy as np
import pandas as pd

from trendalgo.ta.frame_cache import ATTR_READONLY, ATTR_SIGNATURE
from trendalgo.ta.signatures import OhlcvSignature

_MAX_ARRAY_CACHE = 256
_LOCK = threading.Lock()
_NP_CACHE: OrderedDict[
    OhlcvSignature, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
] = OrderedDict()


def _epoch_bounds(df: pd.DataFrame) -> tuple[int, int]:
    idx = df.index
    if isinstance(idx, pd.DatetimeIndex) and len(idx) > 0:
        try:
            return int(idx[0].timestamp()), int(idx[-1].timestamp())
        except (TypeError, ValueError, OSError):
            pass
    return 0, len(df)


def _extract_np(
    df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = len(df)
    c = np.ascontiguousarray(df["close"].to_numpy(dtype=float), dtype=np.float64)
    o = (
        np.ascontiguousarray(df["open"].to_numpy(dtype=float), dtype=np.float64)
        if "open" in df.columns
        else c
    )
    h = (
        np.ascontiguousarray(df["high"].to_numpy(dtype=float), dtype=np.float64)
        if "high" in df.columns
        else c
    )
    lo = (
        np.ascontiguousarray(df["low"].to_numpy(dtype=float), dtype=np.float64)
        if "low" in df.columns
        else c
    )
    v = (
        np.ascontiguousarray(df["volume"].to_numpy(dtype=float), dtype=np.float64)
        if "volume" in df.columns
        else np.ones(n, dtype=np.float64)
    )
    return (o, h, lo, c, v)


def ohlcv_arrays(
    df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return contiguous float64 ``(open, high, low, close, volume)`` arrays."""
    sig = df.attrs.get(ATTR_SIGNATURE)
    n = len(df)
    if isinstance(sig, OhlcvSignature) and sig.bar_count == n:
        with _LOCK:
            hit = _NP_CACHE.get(sig)
            if hit is not None:
                _NP_CACHE.move_to_end(sig)
                return hit
    packed = _extract_np(df)
    if isinstance(sig, OhlcvSignature) and sig.bar_count == n:
        with _LOCK:
            while len(_NP_CACHE) >= _MAX_ARRAY_CACHE:
                _NP_CACHE.popitem(last=False)
            _NP_CACHE[sig] = packed
    return packed


def stamp_scan_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Stamp ``ATTR_SIGNATURE`` / ``ATTR_READONLY`` and cache contiguous arrays."""
    if df is None or df.empty:
        return df
    packed = _extract_np(df)
    _, h, lo, c, v = packed
    first_ts, last_ts = _epoch_bounds(df)
    sample = np.array([c[0], c[-1], h[-1], lo[0], v[-1]], dtype=np.float64)
    price_tag = zlib.crc32(sample.tobytes())
    sig = OhlcvSignature(len(df), first_ts, last_ts, int(price_tag))
    # Keep df.attrs scalar-only (never store np.ndarrays in df.attrs — Pandas concat compares attrs).
    df.attrs[ATTR_SIGNATURE] = sig
    df.attrs[ATTR_READONLY] = True
    with _LOCK:
        while len(_NP_CACHE) >= _MAX_ARRAY_CACHE:
            _NP_CACHE.popitem(last=False)
        _NP_CACHE[sig] = packed
    return df
