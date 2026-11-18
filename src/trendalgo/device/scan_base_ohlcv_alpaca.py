"""Alpaca hour/sub-hour frames for TradFi / Forex All-TA (skip Kraken OHLCVT)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from trendalgo.backtest.heartbeat_tf import exclusive_scan_timeframes, is_subhour_tf
from trendalgo.backtest.load_days import days_for_timeframe, trim_ohlcv_frame
from trendalgo.backtest.ohlcv_resample import frames_from_base
from trendalgo.backtest.ta_fleet import MIN_BARS_FLOOR
from trendalgo.market.ohlcv_disk_cache import load_cached_ohlcv, save_cached_ohlcv
from trendalgo.market.types import OhlcvPoint

_LANE_IDS = frozenset({"tradfi", "forex"})


def is_alpaca_lane(exchange_id: str) -> bool:
    return (exchange_id or "").strip().lower() in _LANE_IDS


def load_alpaca_band_frames(
    *,
    symbol: str,
    pair: str,
    timeframes: tuple[str, ...],
    exchange_id: str,
    prefs_root: Path | None,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Hour TFs from Alpaca 1h; TradFi sub-hour from 1m; Forex skips sub-hour."""
    eid = (exchange_id or "").strip().lower()
    ordered = exclusive_scan_timeframes(timeframes)
    hour_tfs = tuple(tf for tf in ordered if not is_subhour_tf(tf))
    sub_tfs = tuple(tf for tf in ordered if is_subhour_tf(tf))
    frames: dict[str, pd.DataFrame] = {}
    notes: list[str] = []
    sources: list[str] = []
    base_tf = "1h"
    lookback = days_for_timeframe()
    until = datetime.now(tz=UTC)
    since = until - timedelta(days=max(1, lookback))
    cache_pair = _normalize_pair(symbol, pair)

    if hour_tfs:
        frame_1h = _load_alpaca_frame(eid, cache_pair, "1h", since, until, prefs_root=prefs_root)
        if frame_1h is not None and not frame_1h.empty:
            frame_1h = trim_ohlcv_frame(frame_1h, lookback)
            sources.append(f"1h:alpaca:{eid}")
            for tf, frame in frames_from_base(frame_1h, hour_tfs).items():
                if len(frame) >= MIN_BARS_FLOOR:
                    frames[tf] = frame
                else:
                    notes.append(f"{tf}: {len(frame)} bars (<{MIN_BARS_FLOOR})")
        else:
            notes.append("1h Alpaca base unavailable — hour TFs skipped")

    if sub_tfs:
        if eid == "forex":
            notes.append("Forex: sub-hour TFs skipped (Alpaca FX has no 1m)")
        else:
            base_tf = "1m" if not hour_tfs else base_tf
            frame_1m = _load_alpaca_frame(
                eid, cache_pair, "1m", since, until, prefs_root=prefs_root
            )
            if frame_1m is None or frame_1m.empty:
                notes.append("1m Alpaca base unavailable — sub-hour TFs skipped")
            else:
                sources.append(f"1m:alpaca:{eid}")
                for tf, frame in frames_from_base(frame_1m, sub_tfs).items():
                    if len(frame) >= MIN_BARS_FLOOR:
                        frames[tf] = frame
                    else:
                        notes.append(f"{tf}: {len(frame)} bars (<{MIN_BARS_FLOOR})")

    return frames, {
        "data_source": "+".join(sources) if sources else "none",
        "cache_age_s": None,
        "notes": notes,
        "base_tf": base_tf,
        "n_frames": len(frames),
        "deep_1m": False,
        "exchange_id": eid,
    }


def _normalize_pair(symbol: str, pair: str) -> str:
    text = str(pair or "").strip().upper()
    if "/" not in text:
        text = f"{str(symbol).strip().upper()}/USD"
    return text


def _load_alpaca_frame(
    exchange_id: str,
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    prefs_root: Path | None,
) -> pd.DataFrame | None:
    points: list[OhlcvPoint] | None = None
    if prefs_root is not None:
        cached = load_cached_ohlcv(prefs_root, pair, timeframe, since, until)
        if cached and not _is_synthetic_volume(cached):
            points = cached
    if not points:
        points = _fetch_points(exchange_id, pair, timeframe, since, until)
        if points and prefs_root is not None and not _is_synthetic_volume(points):
            save_cached_ohlcv(prefs_root, pair, timeframe, since, until, points)
    if not points or _is_synthetic_volume(points):
        return None
    return _points_to_frame(points)


def _is_synthetic_volume(points: list[OhlcvPoint]) -> bool:
    sample = points[:20] if len(points) > 20 else points
    if not sample:
        return True
    return {round(float(p.volume), 4) for p in sample} == {1000.0}


def _fetch_points(
    exchange_id: str,
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
) -> list[OhlcvPoint] | None:
    try:
        if exchange_id == "forex":
            from trendalgo.market.alpaca_forex import AlpacaForexRatesProvider

            provider = AlpacaForexRatesProvider(allow_synthetic_fallback=False)
            points = provider.fetch("alpaca", pair, timeframe, since, until)
            if str(getattr(provider, "last_source", "")) != "alpaca":
                return None
            return points
        from trendalgo.market.alpaca_ohlcv import AlpacaOhlcvProvider

        return AlpacaOhlcvProvider(allow_synthetic_fallback=False).fetch(
            "alpaca", pair, timeframe, since, until
        )
    except Exception:  # noqa: BLE001
        return None


def _points_to_frame(points: list[OhlcvPoint]) -> pd.DataFrame:
    rows = [
        {
            "timestamp": pd.Timestamp(p.time, unit="s", tz="UTC"),
            "open": float(p.open),
            "high": float(p.high),
            "low": float(p.low),
            "close": float(p.close),
            "volume": float(p.volume),
        }
        for p in points
    ]
    return pd.DataFrame(rows).set_index("timestamp").sort_index()
