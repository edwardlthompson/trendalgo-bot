"""Polygon/CMC OHLCV fallback stub — empty unless CMC_API_KEY present (no live fetch yet)."""

from __future__ import annotations

import os
from typing import Any


class PriceHistoryFallbackClient:
    def __init__(self, **_kwargs: Any) -> None:
        self.cmc_api_key = os.environ.get("CMC_API_KEY", "").strip()
        self.polygon_api_key = os.environ.get("POLYGON_API_KEY", "").strip()

    def get_30d_prices(self, symbol: str) -> tuple[list[float] | None, str]:
        _ = symbol
        return None, "unavailable"

    def get_polygon_30d_hourly_ohlcv(self, symbol: str) -> list[dict[str, float]] | None:
        _ = symbol
        return None

    def get_polygon_30d_daily_ohlcv(self, symbol: str) -> list[dict[str, float]] | None:
        _ = symbol
        return None

    def get_cmc_hourly_ohlcv(self, symbol: str, days: int = 30) -> list[dict[str, float]] | None:
        _ = symbol, days
        return None

    def get_cmc_daily_closes(self, symbol: str) -> list[float] | None:
        _ = symbol
        return None
