"""Deterministic synthetic prices for offline tests and fallback."""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime

from trendalgo.market.symbols import base_symbol
from trendalgo.market.types import OhlcvPoint, PricePoint

_ANCHOR_PRICES: dict[str, float] = {
    "BTC": 98_000.0,
    "ETH": 3_400.0,
    "SOL": 180.0,
    "BNB": 620.0,
    "XRP": 0.62,
    "ADA": 0.55,
    "DOGE": 0.14,
    "AVAX": 38.0,
    "DOT": 7.5,
    "LINK": 16.0,
}


def btc_usd_price_at(ts: datetime, *, anchor: datetime | None = None) -> float:
    anchor = anchor or datetime.now(UTC)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    days = max(0.0, (anchor - ts).total_seconds() / 86_400)
    progress = min(days, 365.0) / 365.0
    base = 42_000.0 + 56_000.0 * (1.0 - progress)
    wave = math.sin(days / 17.0) * 2_800.0 + math.sin(days / 5.3) * 900.0
    return round(max(28_000.0, base + wave), 2)


def _token_drift(symbol: str) -> float:
    digest = hashlib.sha256(symbol.encode()).hexdigest()
    return 0.0004 + (int(digest[:2], 16) / 255) * 0.0009


def token_usd_price_at(symbol: str, ts: datetime, *, anchor: datetime | None = None) -> float:
    anchor = anchor or datetime.now(UTC)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    days = max(0.0, (anchor - ts).total_seconds() / 86_400)
    base = _ANCHOR_PRICES.get(symbol, 100.0)
    progress = min(days, 365.0) / 365.0
    trend = base * (0.82 + 0.28 * (1.0 - progress))
    wave = math.sin(days / (11.0 + _token_drift(symbol) * 100)) * base * 0.04
    return round(max(base * 0.55, trend + wave), 6 if base < 1 else 2)


def synthetic_ohlcv(
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
) -> list[OhlcvPoint]:
    sym = base_symbol(symbol)
    closes = synthetic_series(sym, timeframe, since, until)
    out: list[OhlcvPoint] = []
    for pt in closes:
        c = float(pt.close)
        wobble = c * 0.002
        out.append(
            OhlcvPoint(
                time=pt.time,
                open=c - wobble * 0.3,
                high=c + wobble,
                low=c - wobble,
                close=c,
                volume=1_000.0,
            )
        )
    return out


def synthetic_series(
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
) -> list[PricePoint]:
    sym = base_symbol(symbol)
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    step = 3_600 if timeframe == "1h" else 86_400
    anchor = until
    points: list[PricePoint] = []
    ts = int(since.timestamp())
    end = int(until.timestamp())
    price_fn = (
        btc_usd_price_at
        if sym == "BTC"
        else lambda t, anchor=anchor: token_usd_price_at(sym, t, anchor=anchor)
    )
    while ts <= end:
        dt = datetime.fromtimestamp(ts, tz=UTC)
        points.append(PricePoint(time=ts, close=price_fn(dt, anchor=anchor)))
        ts += step
    return points
