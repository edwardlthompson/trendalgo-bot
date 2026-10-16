"""Exchange balances must match the journal's expected positions (E3).

The expected total of an asset is its checkpoint, plus the signed quantity our orders have
filled since that checkpoint. The first check of an asset takes a checkpoint, so holdings that
existed before the bot traded are not unexplained. Any other difference is a mismatch, and the
exchange halts (trading/reconcile.py). Checks run only when no order of ours is unsettled.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from trendalgo.trading.order_journal import OrderJournal

BALANCE_TOLERANCE = 1e-7  # base units; Kraken amounts carry at most 8 decimals


@dataclass(frozen=True)
class BalanceMismatch:
    asset: str
    expected: float
    actual: float

    def describe(self) -> str:
        return f"{self.asset} expected {self.expected:.8f}, exchange shows {self.actual:.8f}"


def balance_total(balance: dict[str, Any], asset: str) -> float:
    """Total held of one asset in a ccxt balance. An asset that is missing counts as zero."""
    value = (balance.get("total") or {}).get(asset)
    if value is None:
        value = (balance.get(asset) or {}).get("total")
    return float(value or 0.0)


def fill_flows(journal: OrderJournal, exchange: str) -> dict[str, float]:
    """Signed base quantity our orders have moved, per asset: buys add, sells subtract."""
    flows: dict[str, float] = {}
    for row in journal.rows(exchange):
        asset = str(row["pair"]).split("/")[0]
        sign = 1.0 if row["side"] == "buy" else -1.0
        flows[asset] = flows.get(asset, 0.0) + sign * float(row["filled"])
    return flows


def take_checkpoint(
    journal: OrderJournal, exchange: str, asset: str, total: float, flow: float
) -> None:
    """Store the holding that matches our fills up to now. Later checks count from here."""
    journal.run(
        "INSERT INTO balance_checkpoints (exchange, asset, total, applied, checked_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(exchange, asset) DO UPDATE SET "
        "total = excluded.total, applied = excluded.applied, checked_at = excluded.checked_at",
        (exchange, asset, total, flow, time.time()),
    )


def check_balances(
    journal: OrderJournal, balance: dict[str, Any], exchange: str, assets: set[str]
) -> list[BalanceMismatch]:
    """Compare each watched asset with its expected total. A match moves its checkpoint."""
    flows = fill_flows(journal, exchange)
    mismatches: list[BalanceMismatch] = []
    for asset in sorted(assets | set(flows)):
        actual = balance_total(balance, asset)
        flow = flows.get(asset, 0.0)
        point = _checkpoint(journal, exchange, asset)
        if point is None:  # first sight: the current holding is the baseline
            take_checkpoint(journal, exchange, asset, actual, flow)
            continue
        total, applied = point
        expected = total + flow - applied
        if abs(actual - expected) > BALANCE_TOLERANCE:
            mismatches.append(BalanceMismatch(asset, expected, actual))
        else:
            take_checkpoint(journal, exchange, asset, actual, flow)
    return mismatches


def _checkpoint(journal: OrderJournal, exchange: str, asset: str) -> tuple[float, float] | None:
    rows = journal.run(
        "SELECT total, applied FROM balance_checkpoints WHERE exchange = ? AND asset = ?",
        (exchange, asset),
    )
    return (float(rows[0][0]), float(rows[0][1])) if rows else None
