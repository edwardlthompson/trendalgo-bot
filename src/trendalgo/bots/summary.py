"""Bot list enrichment (P/L from trade journal)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from trendalgo.risk.journal import TradeJournal


def _price_at_time(chart: list[dict[str, int | float]], created_at: str) -> float | None:
    if not chart:
        return None
    try:
        ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return float(chart[-1]["value"])
    best = chart[0]
    best_delta = abs(int(best["time"]) - ts)
    for point in chart:
        delta = abs(int(point["time"]) - ts)
        if delta < best_delta:
            best = point
            best_delta = delta
    return float(best["value"])


def bot_pnl_breakdown(
    journal: TradeJournal,
    bot_id: int,
    *,
    chart: list[dict[str, int | float]] | None = None,
    current_price: float | None = None,
) -> dict[str, float | int]:
    trades = journal.list_trades_for_bot(bot_id)
    realized = round(sum(float(t.get("pnl_usd", 0)) for t in trades), 2)

    open_lots: list[tuple[float, float]] = []
    for trade in trades:
        side = str(trade["side"]).lower()
        stake = float(trade["stake_usd"])
        if stake <= 0:
            continue
        entry_px = _price_at_time(chart or [], str(trade["created_at"]))
        if side == "buy":
            if entry_px and entry_px > 0:
                open_lots.append((stake, entry_px))
            continue
        remaining = stake
        while remaining > 0 and open_lots:
            lot_stake, lot_px = open_lots[0]
            take = min(remaining, lot_stake)
            lot_stake -= take
            remaining -= take
            if lot_stake <= 1e-9:
                open_lots.pop(0)
            else:
                open_lots[0] = (lot_stake, lot_px)

    mark = current_price
    if mark is None and chart:
        mark = float(chart[-1]["value"])
    unrealized = 0.0
    if mark and mark > 0:
        for lot_stake, lot_px in open_lots:
            if lot_px > 0:
                unrealized += lot_stake * ((mark - lot_px) / lot_px)
    unrealized = round(unrealized, 2)
    total = round(realized + unrealized, 2)

    return {
        "realized_pnl_usd": realized,
        "unrealized_pnl_usd": unrealized,
        "pnl_usd": total,
        "trade_count": len(trades),
    }


def enrich_bots(
    bots: list[dict[str, Any]],
    journal: TradeJournal,
    *,
    price_by_pair: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for bot in bots:
        pair = str(bot["pair"])
        mark = (price_by_pair or {}).get(pair)
        breakdown = bot_pnl_breakdown(journal, int(bot["id"]), current_price=mark)
        equity = float(bot["equity_usd"])
        total = float(breakdown["pnl_usd"])
        enriched.append(
            {
                **bot,
                "realized_pnl_usd": float(breakdown["realized_pnl_usd"]),
                "unrealized_pnl_usd": float(breakdown["unrealized_pnl_usd"]),
                "pnl_usd": total,
                "pnl_pct": (total / equity) if equity > 0 else 0.0,
                "trade_count": int(breakdown["trade_count"]),
            }
        )
    return enriched


def enrich_bots_with_market(
    bots: list[dict[str, Any]],
    journal: TradeJournal,
    data_dir: Any,
) -> list[dict[str, Any]]:
    from pathlib import Path

    from trendalgo.market.service import PriceHistoryService

    service = PriceHistoryService(Path(data_dir) / "prices.db")
    price_by_pair: dict[str, float] = {}
    for bot in bots:
        pair = str(bot["pair"])
        if pair not in price_by_pair:
            px = last_close_for_pair(
                journal,
                pair,
                str(bot.get("timeframe") or "1h"),
                service,
            )
            if px is not None:
                price_by_pair[pair] = px
    return enrich_bots(bots, journal, price_by_pair=price_by_pair)


def last_close_for_pair(
    journal: TradeJournal,
    pair: str,
    timeframe: str,
    price_service: Any,
) -> float | None:
    """Best-effort mark price for unrealized P/L on fleet cards."""
    del journal
    until = datetime.now(UTC)
    since = until.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        points = price_service.get_closes(pair, timeframe, since, until)
    except Exception:
        return None
    if not points:
        return None
    return float(points[-1].close)
