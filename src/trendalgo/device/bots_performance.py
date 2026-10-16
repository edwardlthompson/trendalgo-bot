"""Aggregate journal PnL per bot, including soft-retired bots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.risk.journal import TradeJournal


@dataclass(frozen=True)
class BotPerfRow:
    bot_id: int
    label: str
    pair: str
    strategy: str
    trade_count: int
    win_count: int
    realized_pnl: float
    retired: bool

    @property
    def win_rate(self) -> float | None:
        if self.trade_count <= 0:
            return None
        return self.win_count / self.trade_count

    @property
    def display_label(self) -> str:
        base = self.label or f"Bot {self.bot_id}"
        return f"{base} (removed)" if self.retired else base


def performance_rows(
    bots_path: Path,
    journal_path: Path,
    *,
    limit_trades: int = 10_000,
) -> list[BotPerfRow]:
    """Rank active + retired bots that have journal credit (best PnL first)."""
    labels: dict[int, dict[str, Any]] = {}
    if bots_path.is_file():
        orch = BotOrchestrator(bots_path)
        for bot in orch.list_bots(include_retired=True):
            labels[int(bot["id"])] = bot
    if not journal_path.is_file():
        return []
    trades = TradeJournal(journal_path).list_trades(limit=limit_trades)
    buckets: dict[int, dict[str, float | int]] = {}
    for trade in trades:
        raw_id = trade.get("bot_id")
        if raw_id is None:
            continue
        try:
            bot_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        bucket = buckets.setdefault(bot_id, {"trades": 0, "wins": 0, "pnl": 0.0})
        bucket["trades"] = int(bucket["trades"]) + 1
        pnl = float(trade.get("pnl_usd") or 0.0)
        bucket["pnl"] = float(bucket["pnl"]) + pnl
        if pnl > 0:
            bucket["wins"] = int(bucket["wins"]) + 1
    rows: list[BotPerfRow] = []
    for bot_id, stats in buckets.items():
        meta = labels.get(bot_id, {})
        deleted = meta.get("deleted_at")
        rows.append(
            BotPerfRow(
                bot_id=bot_id,
                label=str(meta.get("label") or f"Bot {bot_id}"),
                pair=str(meta.get("pair") or ""),
                strategy=str(meta.get("strategy_id") or ""),
                trade_count=int(stats["trades"]),
                win_count=int(stats["wins"]),
                realized_pnl=float(stats["pnl"]),
                retired=bool(deleted) or bot_id not in labels,
            )
        )
    rows.sort(key=lambda r: r.realized_pnl, reverse=True)
    return rows
