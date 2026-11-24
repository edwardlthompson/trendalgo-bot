"""Coin events timeline payload for Avalonia (AV-G-RES4)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.results_store.desk_surfaces import load_events_surface

__all__ = ["events_timeline_payload"]


def events_timeline_payload(root: Path, coin: dict[str, Any], pair: str) -> dict[str, Any]:
    """Full coin-events dialog payload: rows + 30d closes + copy."""
    from trendalgo.device import strings as S
    from trendalgo.device.calendar.coin_window import parse_event_day
    from trendalgo.device.calendar.quota import effective_ahead_days
    from trendalgo.device.calendar.timeline_layout import pack_callouts

    raw = load_events_surface(root, coin)
    closes = _closes_30d(coin)
    symbol = str(coin.get("symbol") or pair or "")
    ahead = effective_ahead_days("free")
    today = datetime.now().astimezone().date()
    start = today - timedelta(days=30)
    end = today + timedelta(days=max(1, ahead))
    span = max(1, (end - start).days)
    packed = pack_callouts(
        [
            (
                day,
                str(r.get("title") or ""),
                str(r.get("displayed_date") or r.get("date") or "")[:10],
                bool(r.get("is_estimated")),
                str(r.get("url") or ""),
            )
            for r in raw
            if (day := parse_event_day(str(r.get("date") or ""))) is not None
        ]
    )
    by_key = {
        (str(r.get("title") or ""), str(r.get("displayed_date") or r.get("date") or "")[:10]): r
        for r in raw
    }
    rows: list[dict[str, Any]] = []
    for m in packed:
        frac = max(0.0, min(1.0, (m.day - start).days / span))
        note = S.COIN_EVENTS_ESTIMATED if m.is_estimated else ""
        if m.show_callout:
            note = f"{note} ★".strip() if note else "★"
        src = by_key.get((m.title, m.displayed_date)) or {}
        rows.append(
            {
                "index": m.index,
                "date": m.displayed_date,
                "title": m.title,
                "source": str(src.get("source") or src.get("category") or ""),
                "note": note,
                "url": m.url,
                "is_estimated": m.is_estimated,
                "marker_frac": round(frac, 4),
                "show_callout": m.show_callout,
            }
        )
    return {
        "pair": pair,
        "symbol": symbol,
        "rows": rows,
        "closes": closes,
        "hint": S.COIN_EVENTS_HINT,
        "empty": S.COIN_EVENTS_NONE,
        "title": S.COIN_EVENTS_TITLE.format(symbol=symbol or pair),
        "estimated_label": S.COIN_EVENTS_ESTIMATED,
        "count": len(rows),
        "ahead_days": ahead,
    }


def _closes_30d(coin: dict[str, Any]) -> list[float]:
    raw = coin.get("spark_closes_30d") or coin.get("closes_1h") or coin.get("chart_closes_1h") or []
    out: list[float] = []
    if not isinstance(raw, list):
        return out
    for x in raw:
        if isinstance(x, int | float):
            out.append(float(x))
    return out
