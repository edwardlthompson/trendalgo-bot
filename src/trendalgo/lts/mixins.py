"""Native strategy mixin — LTS trend + uniformity (T22)."""

from __future__ import annotations

from typing import Any

from trendalgo.lts.adapter import LtsAdapter
from trendalgo.lts.uniformity import uniformity_score


class TrendSpotterMixin:
    """Mixin for native strategies; call from populate_indicators."""

    lts_pair: str = "BTC/USD"
    lts_lookback: int = 20

    def _lts_adapter(self) -> LtsAdapter:
        return LtsAdapter(pair=self.lts_pair)

    def lts_uniform_score(self, dataframe: Any) -> float:
        """Compute uniformity from strategy dataframe OHLCV columns."""
        if dataframe is None or len(dataframe) < self.lts_lookback:
            return 0.5
        rows = dataframe[["date", "open", "high", "low", "close", "volume"]].values.tolist()
        # date column may be datetime or ms timestamp
        normalized: list[list[float]] = []
        for row in rows:
            ts = row[0]
            ts_ms = int(ts.timestamp() * 1000) if hasattr(ts, "timestamp") else int(ts)
            normalized.append([ts_ms, *row[1:6]])
        bars = self._lts_adapter().normalize_bars(normalized)
        return uniformity_score(bars, lookback=self.lts_lookback)

    def lts_trend_bullish(self, dataframe: Any, threshold: float = 0.55) -> bool:
        return self.lts_uniform_score(dataframe) >= threshold
