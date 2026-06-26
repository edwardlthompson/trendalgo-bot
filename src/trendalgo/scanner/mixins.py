"""OpportunityScannerMixin + TrendSpotter Boost (O8, O13)."""

from __future__ import annotations

from typing import Any

from trendalgo.lts.mixins import TrendSpotterMixin


class OpportunityScannerMixin(TrendSpotterMixin):
    """Boost entries when scanner uniformity gate passes."""

    scanner_boost_enabled: bool = True
    scanner_uniformity_min: float = 0.55
    scanner_whitelist: tuple[str, ...] = ()

    def scanner_allows_pair(self, pair: str) -> bool:
        if not self.scanner_whitelist:
            return True
        return pair in self.scanner_whitelist

    def scanner_entry_ok(self, dataframe: Any) -> bool:
        if not self.scanner_boost_enabled:
            return True
        return self.lts_trend_bullish(dataframe, threshold=self.scanner_uniformity_min)
