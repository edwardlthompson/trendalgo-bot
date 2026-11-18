"""Exclusive-band OHLCV load when Kraken OHLCVT deep 1m is unavailable."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

from trendalgo.backtest.heartbeat_tf import exclusive_scan_timeframes, is_subhour_tf
from trendalgo.backtest.load_days import SCAN_LOOKBACK_DAYS, days_for_timeframe, trim_ohlcv_frame
from trendalgo.backtest.ohlcv_resample import frames_from_base
from trendalgo.backtest.ta_fleet import MIN_BARS_FLOOR

SUBHOUR_LOOKBACK_HOURS = 12


def load_exclusive_band_frames(
    *,
    symbol: str,
    pair: str,
    timeframes: tuple[str, ...],
    loader: Any,
    gecko_id: str | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    ordered = exclusive_scan_timeframes(timeframes)
    hour_tfs = tuple(tf for tf in ordered if not is_subhour_tf(tf))
    sub_tfs = tuple(tf for tf in ordered if is_subhour_tf(tf))
    frames: dict[str, pd.DataFrame] = {}
    notes: list[str] = []
    sources: list[str] = []
    base_tf = "1h"
    if hour_tfs:
        lookback = days_for_timeframe()
        loaded = loader.load(symbol=symbol, timeframe="1h", days=lookback, gecko_id=gecko_id)
        frame_1h = loaded.frame if loaded is not None else None
        src = str(getattr(loaded, "source", "") or "none") if loaded is not None else "none"
        sources.append(f"1h:{src}")
        if frame_1h is not None and not frame_1h.empty:
            frame_1h = trim_ohlcv_frame(frame_1h, lookback)
            for tf, frame in frames_from_base(frame_1h, hour_tfs).items():
                if len(frame) >= MIN_BARS_FLOOR:
                    frames[tf] = frame
                else:
                    notes.append(f"{tf}: {len(frame)} bars (<{MIN_BARS_FLOOR})")
        else:
            notes.append("1h base unavailable — hour TFs skipped")
    elif sub_tfs:
        base_tf = "1m"
        frame_1m = fetch_tf_frame(symbol=symbol, pair=pair, timeframe="1m", days=1)
        if frame_1m is None or frame_1m.empty:
            notes.append("1m base unavailable — sub-hour TFs skipped")
        else:
            notes.append(
                f"Sub-hour window ≈{len(frame_1m) / 60.0:.0f}h "
                f"(Kraken OHLC ~{SUBHOUR_LOOKBACK_HOURS}h cap)"
            )
            sources.append("1m:kraken_public")
            for tf, frame in frames_from_base(frame_1m, sub_tfs).items():
                if len(frame) >= MIN_BARS_FLOOR:
                    frames[tf] = frame
                else:
                    notes.append(f"{tf}: {len(frame)} bars (<{MIN_BARS_FLOOR})")
    return frames, {
        "data_source": "+".join(sources) if sources else "none",
        "cache_age_s": _cache_age_seconds(loader, symbol) if hour_tfs else None,
        "notes": notes,
        "base_tf": base_tf,
        "n_frames": len(frames),
        "deep_1m": False,
    }


def fetch_tf_frame(
    *,
    symbol: str,
    pair: str,
    timeframe: str,
    days: int = SCAN_LOOKBACK_DAYS,
    exchange_id: str = "kraken",
) -> pd.DataFrame | None:
    from trendalgo.market.ohlcv_provider import fetch_ohlcv

    text = str(pair or "").strip().upper()
    if "/" not in text:
        text = f"{str(symbol).strip().upper()}/USD"
    until = datetime.now(tz=UTC)
    since = until - timedelta(days=max(1, int(days)))
    try:
        points = fetch_ohlcv(exchange_id, text, timeframe, since, until)
    except Exception:
        return None
    if not points:
        return None
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
    frame = pd.DataFrame(rows).set_index("timestamp").sort_index()
    return frame[~frame.index.duplicated(keep="last")]


def _cache_age_seconds(loader: Any, symbol: str) -> float | None:
    cache = getattr(loader, "cache", None)
    if cache is None or not hasattr(cache, "peek_fetched_at"):
        return None
    try:
        fetched = cache.peek_fetched_at("kraken", symbol, "1h")
    except Exception:
        return None
    if fetched is None:
        return None
    import time

    return max(0.0, time.time() - float(fetched))
