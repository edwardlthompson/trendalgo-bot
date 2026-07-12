"""Live OHLCV acquisition for scanner runs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from trendalgo.market.kraken import fetch_ohlcv
from trendalgo.market.types import OhlcvPoint


@dataclass(frozen=True)
class LiveMarketRow:
    pair: str
    bars: list[OhlcvPoint]
    gain_pct: float
    volume_usd: float

    @property
    def as_of(self) -> datetime:
        return datetime.fromtimestamp(self.bars[-1].time, tz=UTC)


def fetch_live_market(
    pairs: list[str],
    *,
    timeout_seconds: float = 10.0,
    max_retries: int = 3,
    backoff_seconds: float = 0.5,
) -> list[LiveMarketRow]:
    """Fetch one atomic scanner universe, retrying each bounded request."""
    until = datetime.now(UTC)
    since = until - timedelta(hours=3)
    return [
        _fetch_pair(
            pair,
            since,
            until,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )
        for pair in pairs
    ]


def _fetch_pair(
    pair: str,
    since: datetime,
    until: datetime,
    *,
    timeout_seconds: float,
    max_retries: int,
    backoff_seconds: float,
) -> LiveMarketRow:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            bars = fetch_ohlcv(
                pair,
                "5m",
                since,
                until,
                timeout_ms=max(1, int(timeout_seconds * 1000)),
            )[-25:]
            if len(bars) < 2:
                raise RuntimeError(f"insufficient live OHLCV for {pair}")
            first, last = bars[0].close, bars[-1].close
            if first <= 0:
                raise RuntimeError(f"invalid live OHLCV for {pair}")
            return LiveMarketRow(
                pair=pair,
                bars=bars,
                gain_pct=(last / first) - 1.0,
                volume_usd=sum(bar.volume * bar.close for bar in bars),
            )
        except Exception as exc:
            last_error = exc
            if attempt + 1 < max_retries:
                time.sleep(backoff_seconds * (2**attempt))
    raise last_error or RuntimeError(f"live OHLCV fetch failed for {pair}")
