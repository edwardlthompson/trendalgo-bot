"""Load the densest base OHLCV frame for All-TA / pair scans (1m or 1h, 30d)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

from trendalgo.backtest.heartbeat_tf import needs_1m_base
from trendalgo.backtest.load_days import SCAN_LOOKBACK_DAYS, days_for_timeframe, trim_ohlcv_frame


def load_base_ohlcv_frame(
    *,
    symbol: str,
    pair: str,
    timeframes: tuple[str, ...],
    loader: Any,
    gecko_id: str | None = None,
) -> tuple[pd.DataFrame | None, str, str, float | None]:
    """Return (frame, base_tf, source, cache_age_s). Uses 1m when any sub-hour TF is selected."""
    lookback = days_for_timeframe()
    if needs_1m_base(timeframes):
        frame = fetch_1m_frame(symbol=symbol, pair=pair, days=lookback)
        if frame is not None and not frame.empty:
            return trim_ohlcv_frame(frame, lookback), "1m", "kraken_public", None
        return None, "1m", "none", None
    loaded = loader.load(
        symbol=symbol,
        timeframe="1h",
        days=lookback,
        gecko_id=gecko_id,
    )
    frame = loaded.frame if loaded is not None else None
    source = str(getattr(loaded, "source", "") or "none") if loaded is not None else "none"
    age_s = _cache_age_seconds(loader, symbol) if "cache" in source.lower() else None
    if frame is None or frame.empty:
        return None, "1h", source, age_s
    return trim_ohlcv_frame(frame, lookback), "1h", source, age_s


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


def fetch_1m_frame(
    *,
    symbol: str,
    pair: str,
    days: int = SCAN_LOOKBACK_DAYS,
    exchange_id: str = "kraken",
) -> pd.DataFrame | None:
    """Paginated ccxt 1m OHLCV → DataFrame indexed by UTC timestamp."""
    from trendalgo.market.ccxt_ohlcv import fetch_exchange_ohlcv

    text = str(pair or "").strip().upper()
    if "/" not in text:
        text = f"{str(symbol).strip().upper()}/USD"
    until = datetime.now(tz=UTC)
    since = until - timedelta(days=max(1, int(days)))
    try:
        points = fetch_exchange_ohlcv(exchange_id, text, "1m", since, until)
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
