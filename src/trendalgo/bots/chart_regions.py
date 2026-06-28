"""Highlight regions between paired buy/sell markers."""

from __future__ import annotations

from typing import Any


def trade_highlight_regions(
    markers: list[dict[str, Any]],
    candles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not markers or not candles:
        return []
    by_time = {int(c["time"]): float(c["close"]) for c in candles}
    times = sorted(by_time)
    if not times:
        return []

    def price_at(ts: int) -> float:
        if ts in by_time:
            return by_time[ts]
        prior = [t for t in times if t <= ts]
        return by_time[prior[-1]] if prior else by_time[times[0]]

    ordered = sorted(markers, key=lambda m: int(m["time"]))
    regions: list[dict[str, Any]] = []
    open_buy: dict[str, Any] | None = None
    for mark in ordered:
        side = str(mark.get("side", "")).lower()
        ts = int(mark["time"])
        if side == "buy":
            open_buy = mark
            continue
        if side != "sell" or open_buy is None:
            continue
        entry_ts = int(open_buy["time"])
        entry_px = price_at(entry_ts)
        exit_px = price_at(ts)
        pnl = mark.get("pnl_usd")
        profitable = float(pnl) >= 0 if pnl is not None else exit_px >= entry_px
        regions.append(
            {
                "time_start": entry_ts,
                "time_end": ts,
                "entry_price": entry_px,
                "exit_price": exit_px,
                "pnl_usd": float(pnl) if pnl is not None else None,
                "profitable": profitable,
            }
        )
        open_buy = None
    return regions
