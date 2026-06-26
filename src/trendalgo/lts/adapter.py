"""LTS OHLCV types and adapter stub until S4.5 full merge."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class OhlcvBar:
    """Single OHLCV candle aligned with LTS backtesting contract."""

    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class LtsAdapter:
    """Read-only bridge to LTS pipeline (no standalone main.py imports)."""

    def __init__(self, pair: str = "BTC/USD") -> None:
        self.pair = pair

    def normalize_bars(self, rows: Sequence[Sequence[float]]) -> list[OhlcvBar]:
        """Convert CCXT OHLCV rows to LTS bar objects."""
        bars: list[OhlcvBar] = []
        for row in rows:
            if len(row) < 6:
                continue
            ts, o, h, lo, c, v = row[:6]
            bars.append(
                OhlcvBar(
                    timestamp_ms=int(ts),
                    open=float(o),
                    high=float(h),
                    low=float(lo),
                    close=float(c),
                    volume=float(v),
                )
            )
        return bars

    def is_ready(self) -> bool:
        """True when native scanner port is active (S4.5 — no standalone submodule)."""
        return True
