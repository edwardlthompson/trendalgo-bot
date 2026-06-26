"""LTS (linear-trend-spotter) adapter — import-safe boundary (Sprint 1 stub)."""

from trendalgo.lts.adapter import LtsAdapter, OhlcvBar
from trendalgo.lts.mixins import TrendSpotterMixin
from trendalgo.lts.uniformity import uniformity_score

__all__ = ["LtsAdapter", "OhlcvBar", "TrendSpotterMixin", "uniformity_score"]
