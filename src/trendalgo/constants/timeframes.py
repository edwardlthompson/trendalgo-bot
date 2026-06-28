"""TradingView-compatible chart intervals (1S through 1W)."""

from __future__ import annotations

TRADINGVIEW_INTERVALS: tuple[str, ...] = (
    "1S",
    "5S",
    "15S",
    "30S",
    "1",
    "3",
    "5",
    "15",
    "30",
    "45",
    "60",
    "120",
    "180",
    "240",
    "1D",
    "1W",
)

TRADINGVIEW_INTERVAL_LABELS: dict[str, str] = {
    "1S": "1 second",
    "5S": "5 seconds",
    "15S": "15 seconds",
    "30S": "30 seconds",
    "1": "1 minute",
    "3": "3 minutes",
    "5": "5 minutes",
    "15": "15 minutes",
    "30": "30 minutes",
    "45": "45 minutes",
    "60": "1 hour",
    "120": "2 hours",
    "180": "3 hours",
    "240": "4 hours",
    "1D": "1 day",
    "1W": "1 week",
}

_LEGACY_TO_TV: dict[str, str] = {"1h": "60", "1d": "1D", "1w": "1W", "4h": "240"}
_TV_TO_CCXT: dict[str, str] = {
    "1S": "1s",
    "5S": "5s",
    "15S": "15s",
    "30S": "30s",
    "1": "1m",
    "3": "3m",
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "45": "45m",
    "60": "1h",
    "120": "2h",
    "180": "3h",
    "240": "4h",
    "1D": "1d",
    "1W": "1w",
}


def normalize_tv_interval(raw: str) -> str:
    key = raw.strip()
    if key in TRADINGVIEW_INTERVALS:
        return key
    return _LEGACY_TO_TV.get(key.lower(), "60")


def timeframe_for_fetch(raw: str) -> str:
    tv = normalize_tv_interval(raw)
    return _TV_TO_CCXT.get(tv, tv.lower())


_CCXT_STEP_SECONDS: dict[str, int] = {
    "1s": 1,
    "5s": 5,
    "15s": 15,
    "30s": 30,
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "45m": 2700,
    "1h": 3600,
    "2h": 7200,
    "3h": 10800,
    "4h": 14400,
    "1d": 86_400,
    "1w": 604_800,
}


def ccxt_interval_seconds(timeframe: str) -> int:
    """Bar duration in seconds for a CCXT/Kraken interval string."""
    key = timeframe.strip().lower()
    return _CCXT_STEP_SECONDS.get(key, 3600)
