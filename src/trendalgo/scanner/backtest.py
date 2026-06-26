"""LTS backtest data loader (O14)."""

from __future__ import annotations

from trendalgo.scanner.snapshot import QualifiedSnapshot


class BacktestDataLoader:
    """Select pairs and timerange hints from qualified snapshot."""

    def __init__(self, snapshot: QualifiedSnapshot | None) -> None:
        self.snapshot = snapshot

    def pairs_for_backtest(self, limit: int = 3) -> list[str]:
        if not self.snapshot:
            return ["BTC/USD"]
        return [o.pair for o in self.snapshot.opportunities[:limit]]

    def suggested_timerange(self) -> str:
        return "20240101-20240201"
