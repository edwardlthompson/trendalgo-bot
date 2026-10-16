"""OHLCV client shim — Kraken first (TrendAlgo host); synthetic fallback only when opted in."""

from __future__ import annotations

import math
import os
from datetime import UTC, datetime, timedelta
from typing import Any

# Common CoinGecko ids → Kraken USD pairs (bridge usually passes symbol.lower()).
_GECKO_TO_KRAKEN = {
    "bitcoin": "BTC/USD",
    "ethereum": "ETH/USD",
    "solana": "SOL/USD",
    "cardano": "ADA/USD",
    "ripple": "XRP/USD",
    "dogecoin": "DOGE/USD",
    "polkadot": "DOT/USD",
    "chainlink": "LINK/USD",
    "avalanche-2": "AVAX/USD",
    "sui": "SUI/USD",
}


def _allow_synthetic() -> bool:
    """Synthetic candles are opt-in: off unless BACKTEST_ALLOW_SYNTHETIC is 1/true/yes/on."""
    if os.environ.get("TRENDALGO_MARKET_SOURCE", "").strip().lower() == "synthetic":
        return True
    flag = os.environ.get("BACKTEST_ALLOW_SYNTHETIC", "0").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def _synthetic_hourly(
    days: int = 30,
    base: float = 100.0,
    *,
    coin_id: str = "x",
) -> list[dict[str, Any]]:
    """Deterministic series; shape depends on coin_id so net returns diverge across coins.

    Every row carries ``synthetic: True`` so the price cache never persists fake candles.
    """
    n = max(24, int(days) * 24)
    end = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    seed = sum((i + 1) * ord(c) for i, c in enumerate((coin_id or "x")[:32]))
    phase = (seed % 628) / 100.0
    trend = 0.04 + (seed % 25) / 100.0  # 4%–28% drift over the window
    wobble = 0.02 + (seed % 15) / 200.0
    rows: list[dict[str, Any]] = []
    for i in range(n):
        ts = end - timedelta(hours=(n - 1 - i))
        # Non-linear path so indicators / B&H differ by coin (not scale-invariant).
        t = i / max(1, n - 1)
        rel = 1.0 + trend * (t**1.15) + wobble * math.sin(i / 5.0 + phase)
        rel += 0.01 * math.sin(i / 13.0 + seed % 7)
        price = max(0.01, base * rel)
        rows.append(
            {
                "ts": float(ts.timestamp()),
                "open": price * 0.999,
                "high": price * 1.01,
                "low": price * 0.99,
                "close": price,
                "volume": 1000.0 + i + (seed % 100),
                "synthetic": True,
            }
        )
    return rows


def _pair_candidates(coin_id: str, symbol: str | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(pair: str) -> None:
        p = pair.strip().upper().replace("USDT", "USD")
        if p and p not in seen and "/" in p:
            seen.add(p)
            out.append(p)

    if symbol:
        add(f"{symbol}/USD" if "/" not in symbol else symbol)
    cid = (coin_id or "").strip()
    if not cid:
        return out
    if "/" in cid:
        add(cid)
        return out
    mapped = _GECKO_TO_KRAKEN.get(cid.lower())
    if mapped:
        add(mapped)
    add(f"{cid.upper()}/USD")
    return out


def fetch_kraken_hourly_rows(
    coin_id: str,
    days: int = 30,
    *,
    symbol: str | None = None,
    timeout_ms: int = 20_000,
) -> list[dict[str, float]] | None:
    """Return LTS-shaped hourly OHLCV rows from Kraken, or None on soft-fail."""
    try:
        from trendalgo.market.kraken import fetch_ohlcv
    except Exception:
        return None

    until = datetime.now(UTC)
    since = until - timedelta(days=max(30, int(days)) + 2)
    last_err: Exception | None = None
    for pair in _pair_candidates(coin_id, symbol):
        try:
            points = fetch_ohlcv(pair, "1h", since, until, timeout_ms=timeout_ms)
            if len(points) < 48:
                continue
            return [
                {
                    "ts": float(p.time),
                    "open": float(p.open),
                    "high": float(p.high),
                    "low": float(p.low),
                    "close": float(p.close),
                    "volume": float(p.volume),
                }
                for p in points
            ]
        except Exception as exc:
            last_err = exc
            continue
    _ = last_err
    return None


class CoinGeckoClient:
    def __init__(self, calls_per_minute: int = 30) -> None:
        self.calls_per_minute = calls_per_minute
        self.api_key = os.environ.get("COINGECKO_API_KEY", "").strip()

    def get_hourly_ohlcv(
        self,
        coin_id: str,
        days: int = 30,
        *,
        symbol: str | None = None,
    ) -> list[dict[str, Any]] | None:
        kraken = fetch_kraken_hourly_rows(coin_id, days=days, symbol=symbol)
        if kraken:
            return kraken
        if not _allow_synthetic():
            return None
        base = 50.0 + (sum(ord(c) for c in (coin_id or symbol or "x")) % 200)
        return _synthetic_hourly(days=days, base=base, coin_id=coin_id or symbol or "x")

    def get_ohlc(self, coin_id: str, days: int = 30) -> list[list[float]] | None:
        hourly = self.get_hourly_ohlcv(coin_id, days=days)
        if not hourly:
            return None
        out: list[list[float]] = []
        for row in hourly[::24]:
            out.append(
                [
                    float(row["ts"]) * 1000,
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                ]
            )
        return out

    def get_market_chart(
        self, coin_id: str, days: int = 30, interval: str = "daily"
    ) -> list[Any] | None:
        _ = interval
        hourly = self.get_hourly_ohlcv(coin_id, days=days)
        if not hourly:
            return None
        return [[float(r["ts"]) * 1000, float(r["close"])] for r in hourly[::24]]
