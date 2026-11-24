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
from trendalgo.device.scan_base_ohlcv_forex_fallback import (
    fetch_forex_h1_algospecial,
    load_covering_cached_ohlcv,
    normalize_fx_cache_pair,
)
from trendalgo.market.ohlcv_disk_cache import load_cached_ohlcv, save_cached_ohlcv
from trendalgo.market.types import OhlcvPoint
from trendalgo.ta.frame_prep import stamp_scan_frame

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
    """Hour TFs from Alpaca 1h (Forex: AlgoSpecial fallback); TradFi sub-hour from 1m."""
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
    cache_pair = (
        normalize_fx_cache_pair(symbol, pair) if eid == "forex" else _normalize_pair(symbol, pair)
    )

    if hour_tfs:
        frame_1h, src = _load_hour_frame(eid, cache_pair, since, until, prefs_root=prefs_root)
        if frame_1h is not None and not frame_1h.empty:
            frame_1h = trim_ohlcv_frame(frame_1h, lookback)
            sources.append(src)
            for tf, frame in frames_from_base(frame_1h, hour_tfs, base_timeframe="1h").items():
                if len(frame) >= MIN_BARS_FLOOR:
                    frames[tf] = frame
                else:
                    notes.append(f"{tf}: {len(frame)} bars (<{MIN_BARS_FLOOR})")
        else:
            notes.append("1h base unavailable — hour TFs skipped")

    if sub_tfs:
        if eid == "forex":
            notes.append("Forex: sub-hour TFs skipped (no 1m on FX feed)")
        else:
            base_tf = "1m" if not hour_tfs else base_tf
            frame_1m = _load_tradfi_frame(cache_pair, "1m", since, until, prefs_root=prefs_root)
            if frame_1m is None or frame_1m.empty:
                notes.append("1m Alpaca base unavailable — sub-hour TFs skipped")
            else:
                sources.append(f"1m:alpaca:{eid}")
                for tf, frame in frames_from_base(frame_1m, sub_tfs, base_timeframe="1m").items():
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


def _load_hour_frame(
    exchange_id: str,
    pair: str,
    since: datetime,
    until: datetime,
    *,
    prefs_root: Path | None,
) -> tuple[pd.DataFrame | None, str]:
    """Return (frame, source_label). Forex/TradFi fall back to covering disk cache."""
    if exchange_id == "forex":
        return _load_forex_hour(pair, since, until, prefs_root=prefs_root)
    frame, src = _load_tradfi_frame_with_source(pair, "1h", since, until, prefs_root=prefs_root)
    if frame is None:
        return None, ""
    return frame, f"1h:{src}:{exchange_id}"


def _load_forex_hour(
    pair: str,
    since: datetime,
    until: datetime,
    *,
    prefs_root: Path | None,
) -> tuple[pd.DataFrame | None, str]:
    points = _fetch_alpaca_forex(pair, "1h", since, until)
    source = "1h:alpaca:forex"
    if not points and prefs_root is not None:
        points = load_covering_cached_ohlcv(prefs_root, pair, "1h", since, until)
        if points:
            source = "1h:cache:forex"
    if not points:
        points = fetch_forex_h1_algospecial(prefs_root, pair, since, until)
        if points:
            source = "1h:algospecial:forex"
    if not points or _is_synthetic_volume(points):
        return None, ""
    if prefs_root is not None and source.startswith("1h:alpaca"):
        save_cached_ohlcv(prefs_root, pair, "1h", since, until, points)
    return _points_to_frame(points), source


def _load_tradfi_frame_with_source(
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    prefs_root: Path | None,
) -> tuple[pd.DataFrame | None, str]:
    points: list[OhlcvPoint] | None = None
    source = "alpaca"
    if prefs_root is not None:
        cached = load_cached_ohlcv(prefs_root, pair, timeframe, since, until)
        if cached and not _is_synthetic_volume(cached):
            points = cached
            source = "cache"
    if not points:
        points = _fetch_points("tradfi", pair, timeframe, since, until)
        if points and prefs_root is not None and not _is_synthetic_volume(points):
            save_cached_ohlcv(prefs_root, pair, timeframe, since, until, points)
            source = "alpaca"
    if (not points or _is_synthetic_volume(points)) and prefs_root is not None:
        covering = load_covering_cached_ohlcv(prefs_root, pair, timeframe, since, until)
        if covering and not _is_synthetic_volume(covering):
            points = covering
            source = "cache"
    if not points or _is_synthetic_volume(points):
        return None, ""
    return _points_to_frame(points), source


def _load_tradfi_frame(
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    prefs_root: Path | None,
) -> pd.DataFrame | None:
    frame, _ = _load_tradfi_frame_with_source(pair, timeframe, since, until, prefs_root=prefs_root)
    return frame


def _is_synthetic_volume(points: list[OhlcvPoint]) -> bool:
    sample = points[:20] if len(points) > 20 else points
    if not sample:
        return True
    return {round(float(p.volume), 4) for p in sample} == {1000.0}


def _fetch_alpaca_forex(
    pair: str, timeframe: str, since: datetime, until: datetime
) -> list[OhlcvPoint] | None:
    try:
        from trendalgo.market.alpaca_forex import AlpacaForexRatesProvider

        provider = AlpacaForexRatesProvider(allow_synthetic_fallback=False)
        points = provider.fetch("alpaca", pair, timeframe, since, until)
        if str(getattr(provider, "last_source", "")) != "alpaca":
            return None
        return points
    except Exception:  # noqa: BLE001
        return None


def _fetch_points(
    exchange_id: str,
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
) -> list[OhlcvPoint] | None:
    """TradFi live fetch (tests may monkeypatch this)."""
    try:
        if exchange_id == "forex":
            return _fetch_alpaca_forex(pair, timeframe, since, until)
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
    return stamp_scan_frame(pd.DataFrame(rows).set_index("timestamp").sort_index())
