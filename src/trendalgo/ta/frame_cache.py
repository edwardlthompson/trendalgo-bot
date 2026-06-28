"""Share read-only OHLCV DataFrames across bots on the same pair+timeframe+signature."""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import pandas as pd

from trendalgo.ta.signatures import OhlcvSignature

MAX_FRAME_CACHE_ENTRIES = 128
ATTR_SIGNATURE = "ohlcv_signature"
ATTR_READONLY = "_frame_cache_readonly"


@dataclass(frozen=True)
class FrameKey:
    pair: str
    fetch_tf: str
    signature: OhlcvSignature


def _build_df(ohlcv: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(
        [
            {
                "timestamp_ms": int(c["time"]) * 1000,
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "volume": float(c["volume"]),
            }
            for c in ohlcv
        ]
    )
    df.index = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
    return df


class OhlcvFrameCache:
    def __init__(self, max_entries: int = MAX_FRAME_CACHE_ENTRIES) -> None:
        self._max = max_entries
        self._entries: OrderedDict[FrameKey, pd.DataFrame] = OrderedDict()
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

    def invalidate_pair_timeframe(self, pair: str, fetch_tf: str) -> None:
        pair_u = pair.upper()
        with self._lock:
            doomed = [k for k in self._entries if k.pair == pair_u and k.fetch_tf == fetch_tf]
            for key in doomed:
                self._entries.pop(key, None)

    def get_or_build(
        self,
        pair: str,
        fetch_tf: str,
        ohlcv: list[dict[str, Any]],
        signature: OhlcvSignature,
    ) -> pd.DataFrame:
        key = FrameKey(pair=pair.upper(), fetch_tf=fetch_tf, signature=signature)
        with self._lock:
            cached = self._entries.get(key)
            if cached is not None:
                self.hits += 1
                self._entries.move_to_end(key)
                return cached
            self.misses += 1
        df = _build_df(ohlcv)
        df.attrs[ATTR_SIGNATURE] = signature
        df.attrs[ATTR_READONLY] = True
        with self._lock:
            while len(self._entries) >= self._max:
                self._entries.popitem(last=False)
                self.evictions += 1
            self._entries[key] = df
        return df


_frames: dict[str, OhlcvFrameCache] = {}


def get_frame_cache(scope: str = "default") -> OhlcvFrameCache:
    if scope not in _frames:
        _frames[scope] = OhlcvFrameCache()
    return _frames[scope]


def reset_frame_cache(scope: str = "default") -> None:
    _frames.pop(scope, None)
