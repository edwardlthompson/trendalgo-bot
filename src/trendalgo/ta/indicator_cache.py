"""Cache indicator compute() outputs per fn+params+OHLCV signature."""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from trendalgo.ta.signatures import OhlcvSignature, canonical_ta_params_hash
from trendalgo.ta.frame_cache import ATTR_SIGNATURE

MAX_INDICATOR_CACHE_ENTRIES = 512


@dataclass(frozen=True)
class IndicatorKey:
    fn: str
    params_hash: str
    signature: OhlcvSignature


class IndicatorOutputCache:
    def __init__(self, max_entries: int = MAX_INDICATOR_CACHE_ENTRIES) -> None:
        self._max = max_entries
        self._entries: OrderedDict[IndicatorKey, dict[str, np.ndarray]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def stats_payload(self) -> dict[str, int]:
        with self._lock:
            return {
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "entries": len(self._entries),
                "max_entries": self._max,
            }

    def invalidate_signature(self, signature: OhlcvSignature) -> None:
        with self._lock:
            doomed = [k for k in self._entries if k.signature == signature]
            for key in doomed:
                self._entries.pop(key, None)

    def invalidate_pair_timeframe(self, pair: str, fetch_tf: str) -> None:
        del pair, fetch_tf
        return

    def get(self, fn: str, signature: OhlcvSignature, params: dict[str, Any]) -> dict[str, np.ndarray] | None:
        key = IndicatorKey(fn.upper(), canonical_ta_params_hash(params), signature)
        with self._lock:
            hit = self._entries.get(key)
            if hit is not None:
                self.hits += 1
                self._entries.move_to_end(key)
                return hit
        return None

    def put(self, fn: str, signature: OhlcvSignature, params: dict[str, Any], out: dict[str, np.ndarray]) -> None:
        key = IndicatorKey(fn.upper(), canonical_ta_params_hash(params), signature)
        stored = {k: np.asarray(v, dtype=float).copy() for k, v in out.items()}
        with self._lock:
            while len(self._entries) >= self._max:
                self._entries.popitem(last=False)
                self.evictions += 1
            self._entries[key] = stored

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_indicators: dict[str, IndicatorOutputCache] = {}


def get_indicator_cache(scope: str = "default") -> IndicatorOutputCache:
    if scope not in _indicators:
        _indicators[scope] = IndicatorOutputCache()
    return _indicators[scope]


def reset_indicator_cache(scope: str = "default") -> None:
    _indicators.pop(scope, None)


def signature_from_df(df: pd.DataFrame) -> OhlcvSignature | None:
    sig = df.attrs.get(ATTR_SIGNATURE)
    if not isinstance(sig, OhlcvSignature):
        return None
    if sig.bar_count != len(df):
        return None
    return sig
