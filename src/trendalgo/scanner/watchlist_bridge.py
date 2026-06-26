"""Scanner → bot pair whitelist bridge (O8)."""

from __future__ import annotations

from trendalgo.scanner.backtest import BacktestDataLoader
from trendalgo.scanner.store import ScannerStore


def pairs_for_bot_whitelist(store: ScannerStore, limit: int = 5) -> list[str]:
    snapshot = store.latest_snapshot()
    loader = BacktestDataLoader(snapshot)
    pinned = store.watchlist()
    pairs = pinned + [p for p in loader.pairs_for_backtest(limit) if p not in pinned]
    return pairs[:limit]
