"""Deterministic trade-journal → equity replay (FEAT-01).

Replaying the same ordered fills into a fresh curve must match bit-for-bit so
disputes and debugging share one backbone with live/paper journals.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from trendalgo.risk.journal import TradeJournal, TradeRecord


@dataclass(frozen=True)
class EquityPoint:
    """One equity observation after applying a fill (or the starting seed)."""

    index: int
    exchange_trade_id: str
    equity_usd: float
    pnl_usd: float


def ordered_fills(journal: TradeJournal, *, bot_id: int | None = None) -> list[dict[str, Any]]:
    """Stable fill order: ascending id / created_at (oldest first)."""
    if bot_id is None:
        rows = journal.list_trades(limit=100_000)
        rows = list(reversed(rows))  # list_trades is newest-first
    else:
        rows = journal.list_trades_for_bot(bot_id, limit=100_000)
    return rows


def replay_equity(
    fills: Sequence[dict[str, Any] | TradeRecord],
    *,
    starting_equity_usd: float,
) -> list[EquityPoint]:
    """Apply fills in order; equity is starting + cumulative realized pnl."""
    if not math.isfinite(starting_equity_usd) or starting_equity_usd < 0:
        raise ValueError("starting_equity_usd must be a finite non-negative number")
    equity = float(starting_equity_usd)
    points: list[EquityPoint] = [
        EquityPoint(index=0, exchange_trade_id="", equity_usd=equity, pnl_usd=0.0)
    ]
    for i, fill in enumerate(fills, start=1):
        if isinstance(fill, TradeRecord):
            trade_id = fill.exchange_trade_id
            pnl = float(fill.pnl_usd)
        else:
            trade_id = str(fill.get("exchange_trade_id") or "")
            pnl = float(fill.get("pnl_usd") or 0.0)
        equity = equity + pnl
        points.append(
            EquityPoint(
                index=i,
                exchange_trade_id=trade_id,
                equity_usd=equity,
                pnl_usd=pnl,
            )
        )
    return points


def equity_fingerprint(points: Sequence[EquityPoint]) -> tuple[tuple[int, str, float, float], ...]:
    """Bit-stable identity for equality tests (floats left as IEEE values)."""
    return tuple((p.index, p.exchange_trade_id, p.equity_usd, p.pnl_usd) for p in points)


def replay_journal_equity(
    journal: TradeJournal,
    *,
    starting_equity_usd: float,
    bot_id: int | None = None,
) -> list[EquityPoint]:
    """Replay a journal into an equity curve."""
    return replay_equity(
        ordered_fills(journal, bot_id=bot_id),
        starting_equity_usd=starting_equity_usd,
    )
