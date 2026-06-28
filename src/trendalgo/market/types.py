"""Shared market data types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PricePoint:
    time: int
    close: float


@dataclass(frozen=True)
class OhlcvPoint:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
