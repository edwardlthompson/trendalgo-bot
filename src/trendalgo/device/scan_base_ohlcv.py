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
) -> tuple[pd.DataFrame | None, str]:
    """Return (frame, base_tf). Uses 1m when any sub-hour TF is selected."""
    lookback = days_for_timeframe()
    if needs_1m_base(timeframes):
        frame = fetch_1m_frame(symbol=symbol, pair=pair, days=lookback)
        if frame is not None and not frame.empty:
            return trim_ohlcv_frame(frame, lookback), "1m"
        return None, "1m"
    loaded = loader.load(
        symbol=symbol,
        timeframe="1h",
        days=lookback,
        gecko_id=gecko_id,
    )
    frame = loaded.frame if loaded is not None else None
    if frame is None or frame.empty:
        return None, "1h"
    return trim_ohlcv_frame(frame, lookback), "1h"


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
