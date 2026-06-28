"""Map journal trades to chart markers with P/L on exits."""

from __future__ import annotations

from typing import Any


def trades_to_chart_markers(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from datetime import datetime

    ordered: list[dict[str, Any]] = []
    for trade in trades:
        iso = str(trade.get("created_at", ""))
        try:
            ts = int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
        except ValueError:
            continue
        ordered.append({**trade, "_ts": ts})
    ordered.sort(key=lambda t: int(t["_ts"]))

    markers: list[dict[str, Any]] = []
    open_stake: float | None = None
    for trade in ordered:
        ts = int(trade["_ts"])
        side = str(trade.get("side", "")).lower()
        if side == "buy":
            open_stake = float(trade.get("stake_usd") or 0) or open_stake
            markers.append({"time": ts, "side": side, "pnl_usd": None, "pnl_pct": None})
            continue
        if side != "sell":
            continue
        stake = float(trade.get("stake_usd") or 0) or float(open_stake or 0)
        pnl = float(trade.get("pnl_usd", 0) or 0)
        pnl_pct = (pnl / stake * 100.0) if stake > 0 else None
        markers.append(
            {
                "time": ts,
                "side": side,
                "pnl_usd": pnl,
                "pnl_pct": pnl_pct,
            }
        )
        open_stake = None
    return markers
