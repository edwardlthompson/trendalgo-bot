"""Display rows: plain text built from stored data. Pure, so every view shows the same wording."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from trendalgo.device import strings as S
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot

SPARK_LEVELS = "▁▂▃▄▅▆▇█"
EMPTY_CELL = "-"


@dataclass(frozen=True)
class ScanRow:
    rank: str
    pair: str
    gain: str
    volume: str
    entry: str
    trend: str


@dataclass(frozen=True)
class BotRow:
    label: str
    pair: str
    state: str
    equity: str
    strategy: str = EMPTY_CELL
    realized: str = EMPTY_CELL
    unrealized: str = EMPTY_CELL


@dataclass(frozen=True)
class TradeRow:
    time: str
    pair: str
    side: str
    pnl: str
    source: str
    pnl_value: float = 0.0


def sparkline(values: list[float]) -> str:
    """A one-line trend from block characters. Empty input gives a dash; a flat series a flat line."""
    finite = [v for v in values if math.isfinite(v)]
    if not finite:
        return EMPTY_CELL
    low, high = min(finite), max(finite)
    top = len(SPARK_LEVELS) - 1
    if high == low:
        return SPARK_LEVELS[0] * len(finite)
    return "".join(SPARK_LEVELS[round((v - low) / (high - low) * top)] for v in finite)


def scan_caption(snapshot: QualifiedSnapshot | None) -> str:
    if snapshot is None:
        return ""
    text = S.SCANNER_CAPTION.format(
        scan_id=snapshot.scan_id,
        as_of=snapshot.as_of.isoformat(timespec="minutes"),
    )
    return text + (S.SCANNER_DEGRADED if snapshot.degraded else "")


def backtest_trade_rows(trades: list[dict[str, Any]]) -> list[tuple[str, ...]]:
    """Table cells for the trades a backtest returned (already plain values)."""
    return [
        (
            str(trade["entry_time"])[:16].replace("T", " "),
            str(trade["exit_time"])[:16].replace("T", " "),
            f"{float(trade['entry_price']):,.4f}",
            f"{float(trade['exit_price']):,.4f}",
            f"{float(trade['pnl_pct']):+.2f}%",
            str(trade["exit_reason"]),
        )
        for trade in trades
    ]


def scan_rows(snapshot: QualifiedSnapshot | None) -> list[ScanRow]:
    if snapshot is None:
        return []
    return [_scan_row(row) for row in snapshot.opportunities]


def _scan_row(row: OpportunityRow) -> ScanRow:
    return ScanRow(
        rank=str(row.rank),
        pair=row.pair,
        gain=f"{row.gain_pct:+.2f}%",
        volume=f"{row.volume_score:.1f}",
        entry="Yes" if row.entry_signal else "No",
        trend=sparkline(row.sparkline),
    )


def bot_rows(bots: list[dict[str, Any]]) -> list[BotRow]:
    return [
        BotRow(
            label=str(bot.get("label", "")),
            pair=str(bot.get("pair", "")),
            state="On" if bot.get("enabled") else "Off",
            equity=_money(bot.get("equity_usd")),
            strategy=str(bot.get("strategy_id") or bot.get("indicator") or EMPTY_CELL),
            realized=_money(bot.get("realized_pnl_usd")),
            unrealized=_money(bot.get("unrealized_pnl_usd")),
        )
        for bot in bots
    ]


def trade_rows(trades: list[dict[str, Any]]) -> list[TradeRow]:
    rows: list[TradeRow] = []
    for trade in trades:
        raw = trade.get("pnl_usd")
        value = float(raw) if isinstance(raw, int | float) and math.isfinite(raw) else 0.0
        rows.append(
            TradeRow(
                time=_when(trade.get("created_at")),
                pair=str(trade.get("pair", "")),
                side=str(trade.get("side", "")),
                pnl=_money(raw),
                source=str(trade.get("signal_source") or EMPTY_CELL),
                pnl_value=value,
            )
        )
    return rows


def _money(value: object) -> str:
    if not isinstance(value, int | float) or not math.isfinite(value):
        return EMPTY_CELL
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def _when(value: object) -> str:
    if not value:
        return EMPTY_CELL
    return str(value)[:16].replace("T", " ")
