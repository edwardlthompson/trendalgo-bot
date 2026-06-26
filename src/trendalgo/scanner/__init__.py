"""Opportunity Scanner — native LTS absorption (ADR-0006, Sprint 4.5)."""

from trendalgo.scanner.backtest import BacktestDataLoader
from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.mixins import OpportunityScannerMixin
from trendalgo.scanner.pipeline import run_pipeline
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore
from trendalgo.scanner.watchlist_bridge import pairs_for_bot_whitelist

__all__ = [
    "BacktestDataLoader",
    "OpportunityRow",
    "OpportunityScannerMixin",
    "QualifiedSnapshot",
    "ScannerSettings",
    "ScannerStore",
    "pairs_for_bot_whitelist",
    "run_pipeline",
]
