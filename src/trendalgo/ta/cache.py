"""Shared TA signal cache — identical bots reuse entries/exits; incremental tail on bar append.

Single-process assumption: each uvicorn worker holds its own in-memory cache (acceptable v1).
On incremental append, indicator cache is not used (fresh compute on tail df only) — see R3 policy.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from trendalgo.constants.timeframes import normalize_tv_interval, timeframe_for_fetch
from trendalgo.ta.frame_cache import ATTR_READONLY, ATTR_SIGNATURE, get_frame_cache
from trendalgo.ta.indicator_cache import get_indicator_cache, reset_indicator_cache
from trendalgo.ta.signals import resolve_preset, signals_for_preset
from trendalgo.ta.signatures import OhlcvSignature, canonical_ta_params_hash

MAX_SIGNAL_CACHE_ENTRIES = 256
WARMUP_MARGIN = 10
WARMUP_FLOOR = 50

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaFingerprint:
    pair: str
    timeframe: str
    strategy_id: str
    ta_params_hash: str

    @classmethod
    def from_bot(cls, bot: dict[str, Any]) -> TaFingerprint:
        params = dict(bot.get("ta_params") or {})
        return cls(
            pair=str(bot["pair"]).upper(),
            timeframe=normalize_tv_interval(str(bot.get("timeframe") or "60")),
            strategy_id=str(bot.get("strategy_id", "")).upper(),
            ta_params_hash=canonical_ta_params_hash(params),
        )


@dataclass
class CachedSignals:
    signature: OhlcvSignature
    entries: np.ndarray
    exits: np.ndarray
    compute_ms: float = 0.0


@dataclass
class TaCacheStats:
    hits_exact: int = 0
    hits_incremental: int = 0
    misses_full: int = 0
    incremental_rejected: int = 0
    invalidations_config: int = 0
    invalidations_ohlcv: int = 0
    evictions: int = 0
    dedupe_savings: int = 0
    stale_fallback: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits_exact": self.hits_exact,
            "hits_incremental": self.hits_incremental,
            "misses_full": self.misses_full,
            "incremental_rejected": self.incremental_rejected,
            "invalidations_config": self.invalidations_config,
            "invalidations_ohlcv": self.invalidations_ohlcv,
            "evictions": self.evictions,
            "dedupe_savings": self.dedupe_savings,
            "stale_fallback": self.stale_fallback,
        }


@dataclass
class CacheMeta:
    hit: str  # exact | incremental | miss
    shared: bool
    warmup_bars: int
    compute_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "hit": self.hit,
            "shared": self.shared,
            "warmup_bars": self.warmup_bars,
            "compute_ms": self.compute_ms,
        }


def ohlcv_list_to_df(
    ohlcv: list[dict[str, Any]],
    *,
    pair: str | None = None,
    fetch_tf: str | None = None,
) -> pd.DataFrame:
    sig = OhlcvSignature.from_ohlcv(ohlcv)
    if pair and fetch_tf:
        df = get_frame_cache().get_or_build(pair, fetch_tf, ohlcv, sig)
    else:
        df = _build_ohlcv_df(ohlcv)
        df.attrs[ATTR_SIGNATURE] = sig
    return df


def _build_ohlcv_df(ohlcv: list[dict[str, Any]]) -> pd.DataFrame:
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


def trim_df_for_bot(df: pd.DataFrame, preset: dict[str, Any], bot: dict[str, Any]) -> pd.DataFrame:
    from trendalgo.bots.limits import max_ohlcv_bars

    warmup = preset_warmup_bars(preset)
    tf = normalize_tv_interval(str(bot.get("timeframe") or "60"))
    cap = max(warmup, max_ohlcv_bars(tf))
    if len(df) <= cap:
        return df
    trimmed = df.iloc[-cap:]
    if df.attrs.get(ATTR_READONLY):
        trimmed = trimmed.copy()
    sig = df.attrs.get(ATTR_SIGNATURE)
    if isinstance(sig, OhlcvSignature):
        trimmed.attrs[ATTR_SIGNATURE] = sig
    return trimmed


def preset_warmup_bars(preset: dict[str, Any]) -> int:
    kind = str(preset.get("kind", ""))
    if kind == "ma_cross":
        base = int(preset.get("slow", 30))
    else:
        base = int(preset.get("timeperiod", preset.get("length", 14)))
    return max(WARMUP_FLOOR, base + WARMUP_MARGIN)


def _can_incremental(cached: CachedSignals, new_sig: OhlcvSignature) -> int:
    old = cached.signature
    if new_sig.bar_count <= old.bar_count:
        return 0
    if new_sig.first_ts != old.first_ts:
        return 0
    if new_sig.last_ts <= old.last_ts:
        return 0
    delta = new_sig.bar_count - old.bar_count
    if delta > 10:
        return 0
    return delta


def _splice_tail(
    cached: CachedSignals,
    df: pd.DataFrame,
    preset: dict[str, Any],
    delta: int,
    warmup: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    tail_df = df.iloc[-warmup:]
    if len(tail_df) < warmup // 2:
        return None
    try:
        tail_entries, tail_exits = signals_for_preset(tail_df, preset)
    except (KeyError, ValueError, TypeError):
        return None
    if len(tail_entries) != len(tail_df) or len(tail_exits) != len(tail_df):
        return None
    if delta > len(tail_entries):
        return None
    entries = np.concatenate([cached.entries, tail_entries[-delta:]])
    exits = np.concatenate([cached.exits, tail_exits[-delta:]])
    if len(entries) != len(df) or len(exits) != len(df):
        return None
    return entries, exits


class CacheCoordinator:
    """Cascade invalidation across frame, indicator, and signal tiers."""

    def __init__(self, cache: TaSignalCache) -> None:
        self._cache = cache

    def invalidate_fingerprint(self, fp: TaFingerprint) -> None:
        self._cache._remove(fp)

    def invalidate_pair_timeframe(self, pair: str, timeframe: str) -> None:
        pair_u = pair.upper()
        tf = normalize_tv_interval(timeframe)
        fetch_tf = timeframe_for_fetch(tf)
        self._cache._remove_matching(lambda fp: fp.pair == pair_u and fp.timeframe == tf)
        get_frame_cache().invalidate_pair_timeframe(pair_u, fetch_tf)

    def on_ohlcv_signature_change(self, pair: str, timeframe: str) -> None:
        self.invalidate_pair_timeframe(pair, timeframe)
        get_indicator_cache().clear()
        self._cache.stats.invalidations_ohlcv += 1


def _signals_for_bot_df(
    df: pd.DataFrame, preset: dict[str, Any], bot: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray]:
    work_df = trim_df_for_bot(df, preset, bot)
    entries, exits = signals_for_preset(work_df, preset)
    if len(entries) == len(df):
        return entries, exits
    pad = len(df) - len(entries)
    if pad <= 0:
        return entries[-len(df) :], exits[-len(df) :]
    return (
        np.concatenate([np.zeros(pad, dtype=bool), entries]),
        np.concatenate([np.zeros(pad, dtype=bool), exits]),
    )


class TaSignalCache:
    def __init__(self, max_entries: int = MAX_SIGNAL_CACHE_ENTRIES) -> None:
        self._max_entries = max_entries
        self._entries: OrderedDict[TaFingerprint, CachedSignals] = OrderedDict()
        self._locks: dict[TaFingerprint, threading.Lock] = {}
        self._global = threading.Lock()
        self.stats = TaCacheStats()
        self.coordinator = CacheCoordinator(self)

    def _lock_for(self, fp: TaFingerprint) -> threading.Lock:
        with self._global:
            if fp not in self._locks:
                self._locks[fp] = threading.Lock()
            return self._locks[fp]

    def _remove(self, fp: TaFingerprint) -> None:
        with self._global:
            self._entries.pop(fp, None)
            self._locks.pop(fp, None)

    def _remove_matching(self, pred: Callable[[TaFingerprint], bool]) -> None:
        with self._global:
            doomed = [fp for fp in self._entries if pred(fp)]
            for fp in doomed:
                self._entries.pop(fp, None)
                self._locks.pop(fp, None)

    def _evict_if_needed(self) -> None:
        while len(self._entries) >= self._max_entries:
            self._entries.popitem(last=False)
            self.stats.evictions += 1

    def _put(self, fp: TaFingerprint, cached: CachedSignals) -> None:
        self._evict_if_needed()
        self._entries[fp] = cached
        self._entries.move_to_end(fp)

    def invalidate_for_bot_config_change(self, old: dict[str, Any], new: dict[str, Any]) -> None:
        keys = ("pair", "timeframe", "strategy_id", "ta_params")
        if all(old.get(k) == new.get(k) for k in keys):
            return
        self.coordinator.invalidate_fingerprint(TaFingerprint.from_bot(old))
        self.coordinator.invalidate_fingerprint(TaFingerprint.from_bot(new))
        self.stats.invalidations_config += 1

    def stats_payload(self) -> dict[str, Any]:
        with self._global:
            entry_count = len(self._entries)
        return {
            **self.stats.to_dict(),
            "entries": entry_count,
            "max_entries": self._max_entries,
            "frame_cache": get_frame_cache().stats_payload(),
            "indicator_cache": get_indicator_cache().stats_payload(),
        }

    def get_or_compute_signals(
        self,
        df: pd.DataFrame,
        ohlcv: list[dict[str, Any]],
        bot: dict[str, Any],
    ) -> tuple[np.ndarray, np.ndarray, CacheMeta]:
        fp = TaFingerprint.from_bot(bot)
        sig = OhlcvSignature.from_ohlcv(ohlcv)
        preset = resolve_preset(fp.strategy_id, dict(bot.get("ta_params") or {}))
        warmup = preset_warmup_bars(preset)
        lock = self._lock_for(fp)

        with lock:
            cached = self._entries.get(fp)
            if cached is not None and cached.signature == sig:
                self.stats.hits_exact += 1
                self.stats.dedupe_savings += 1
                self._entries.move_to_end(fp)
                return (
                    cached.entries,
                    cached.exits,
                    CacheMeta(hit="exact", shared=True, warmup_bars=warmup, compute_ms=0.0),
                )

            delta = _can_incremental(cached, sig) if cached is not None else 0
            if cached is not None and cached.signature != sig and delta == 0:
                self.stats.stale_fallback += 1
                logger.debug(
                    "TA cache stale fallback to full recompute: pair=%s tf=%s strategy=%s",
                    fp.pair,
                    fp.timeframe,
                    fp.strategy_id,
                )
            if cached is not None and delta > 0:
                t0 = time.perf_counter()
                spliced = _splice_tail(cached, df, preset, delta, warmup)
                ms = (time.perf_counter() - t0) * 1000
                if spliced is not None:
                    entries, exits = spliced
                    self._put(
                        fp,
                        CachedSignals(signature=sig, entries=entries, exits=exits, compute_ms=ms),
                    )
                    self.stats.hits_incremental += 1
                    return (
                        entries,
                        exits,
                        CacheMeta(
                            hit="incremental", shared=False, warmup_bars=warmup, compute_ms=ms
                        ),
                    )
                self.stats.incremental_rejected += 1
                logger.debug(
                    "TA cache incremental rejected, full recompute: pair=%s tf=%s strategy=%s",
                    fp.pair,
                    fp.timeframe,
                    fp.strategy_id,
                )

            t0 = time.perf_counter()
            try:
                entries, exits = _signals_for_bot_df(df, preset, bot)
            except (KeyError, ValueError, TypeError):
                empty = np.zeros(len(df), dtype=bool)
                return (
                    empty,
                    empty,
                    CacheMeta(hit="miss", shared=False, warmup_bars=warmup, compute_ms=0.0),
                )
            ms = (time.perf_counter() - t0) * 1000
            self._put(fp, CachedSignals(signature=sig, entries=entries, exits=exits, compute_ms=ms))
            self.stats.misses_full += 1
            return (
                entries,
                exits,
                CacheMeta(hit="miss", shared=False, warmup_bars=warmup, compute_ms=ms),
            )


_caches: dict[str, TaSignalCache] = {}


def get_ta_signal_cache(scope: str = "default") -> TaSignalCache:
    if scope not in _caches:
        _caches[scope] = TaSignalCache()
    return _caches[scope]


def reset_ta_signal_cache(scope: str = "default") -> None:
    _caches.pop(scope, None)


def reset_all_ta_caches(scope: str = "default") -> None:
    from trendalgo.ta.frame_cache import reset_frame_cache

    reset_ta_signal_cache(scope)
    reset_frame_cache(scope)
    reset_indicator_cache(scope)
