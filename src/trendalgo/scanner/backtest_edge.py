"""Signed Bot vs Buy & Hold edge from LTS backtest rows (percentage points).

``bot_vs_bh_pct`` = best non-B&H strategy ``net_pct`` − B&H ``net_pct`` on the same
window. Positive means the bot beat holding; negative means it trailed.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

_BH = "B&H"
EDGE_KEYS = ("bot_vs_bh_pct", "bot_best_net_pct", "buy_hold_net_pct", "bot_best_label")


def _net(row: Any) -> float | None:
    if not isinstance(row, dict):
        return None
    raw = row.get("net_pct")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def bot_vs_bh_edge(
    strategies: Iterable[Any],
    buy_hold: Any,
) -> dict[str, Any] | None:
    """Return edge fields, or ``None`` when the bot or B&H net is missing."""
    buy_hold_net = _net(buy_hold)
    best_net: float | None = None
    best_row: dict[str, Any] | None = None
    for row in strategies:
        if not isinstance(row, dict) or str(row.get("indicator", "")).strip() == _BH:
            continue
        net = _net(row)
        if net is None:
            continue
        if best_net is None or net > best_net:
            best_net, best_row = net, row
    if best_net is None or buy_hold_net is None or best_row is None:
        return None
    label = f"{best_row.get('indicator', '')} {best_row.get('timeframe', '')}".strip()
    return {
        "bot_vs_bh_pct": round(best_net - buy_hold_net, 6),
        "bot_best_net_pct": round(best_net, 6),
        "buy_hold_net_pct": round(buy_hold_net, 6),
        "bot_best_label": label,
    }
