"""On-demand disk cache for TradFi/FX OHLCV (never prefetch-all)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from trendalgo.market.types import OhlcvPoint


def _day_key(symbol: str, timeframe: str, since: datetime, until: datetime) -> str:
    """Day-bucket keys so same-day rescan hits cache (ignore clock seconds)."""
    s = since.strftime("%Y%m%d")
    u = until.strftime("%Y%m%d")
    safe = symbol.replace("/", "_").upper()
    return f"{safe}_{timeframe}_{s}_{u}.json"


def cache_path(root: Path, symbol: str, timeframe: str, since: datetime, until: datetime) -> Path:
    return root / "ohlcv_cache" / _day_key(symbol, timeframe, since, until)


def load_cached_ohlcv(
    root: Path,
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
) -> list[OhlcvPoint] | None:
    path = cache_path(root, symbol, timeframe, since, until)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    rows = raw.get("bars") if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        return None
    out: list[OhlcvPoint] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            OhlcvPoint(
                time=int(row["time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row.get("volume") or 0),
            )
        )
    return out


def save_cached_ohlcv(
    root: Path,
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    points: list[OhlcvPoint],
) -> Path:
    path = cache_path(root, symbol, timeframe, since, until)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": [
            {
                "time": p.time,
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in points
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
