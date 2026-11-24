"""Signed Bot vs Buy & Hold edge from LTS backtest rows (percentage points).

``bot_vs_bh_pct`` = best non-B&H strategy ``net_pct`` − B&H ``net_pct``.
Prefer B&H on the **same timeframe** as the winning strategy when available so the
edge is not inflated/deflated by a different TF's hold return. This is *not* the
board's 30d price gain column.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

_BH = "B&H"
_ORACLE = "Oracle max"
_BASELINES = frozenset({_BH, _ORACLE})
EDGE_KEYS = ("bot_vs_bh_pct", "bot_best_net_pct", "buy_hold_net_pct", "bot_best_label")


def is_baseline_indicator(indicator: object) -> bool:
    """True for B&H / Oracle max ceilings (not eligible for Best BT)."""
    return str(indicator or "").strip() in _BASELINES


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


def _pick_buy_hold(
    buy_hold: Any,
    best_row: dict[str, Any],
    buy_hold_rows: Iterable[Any] | None,
) -> Any:
    """Same-timeframe B&H when present; else the provided best-across-TF fallback."""
    tf = str(best_row.get("timeframe") or "").strip()
    if not tf or buy_hold_rows is None:
        return buy_hold
    for row in buy_hold_rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("indicator") or "").strip() != _BH:
            continue
        if str(row.get("timeframe") or "").strip() == tf and _net(row) is not None:
            return row
    return buy_hold


def bot_vs_bh_edge(
    strategies: Iterable[Any],
    buy_hold: Any,
    *,
    buy_hold_rows: Iterable[Any] | None = None,
) -> dict[str, Any] | None:
    """Return edge fields, or ``None`` when the bot or B&H net is missing."""
    best_net: float | None = None
    best_row: dict[str, Any] | None = None
    for row in strategies:
        if not isinstance(row, dict) or is_baseline_indicator(row.get("indicator")):
            continue
        net = _net(row)
        if net is None:
            continue
        if best_net is None or net > best_net:
            best_net, best_row = net, row
    if best_net is None or best_row is None:
        return None
    chosen_bh = _pick_buy_hold(buy_hold, best_row, buy_hold_rows)
    buy_hold_net = _net(chosen_bh)
    if buy_hold_net is None:
        return None
    # bot_best_* stays the best non-baseline TA (edge math / tip). Board UI may
    # prefer B&H for display when buy_hold_net > best_net (see best_pill / shell).
    label = f"{best_row.get('timeframe', '')} {best_row.get('indicator', '')}".strip()
    return {
        "bot_vs_bh_pct": round(best_net - buy_hold_net, 6),
        "bot_best_net_pct": round(best_net, 6),
        "buy_hold_net_pct": round(buy_hold_net, 6),
        "bot_best_label": label,
        "_edge_buy_hold": chosen_bh if isinstance(chosen_bh, dict) else None,
    }


def bot_vs_bh_cell_tip(coin: dict[str, Any]) -> str:
    """Hover text: Best BT − B&H = edge (explicitly not the 30d price-gain column)."""
    try:
        best = float(coin["bot_best_net_pct"]) if coin.get("bot_best_net_pct") is not None else None
    except (TypeError, ValueError):
        best = None
    try:
        vs = float(coin["bot_vs_bh_pct"]) if coin.get("bot_vs_bh_pct") is not None else None
    except (TypeError, ValueError):
        vs = None
    bh_net = coin.get("buy_hold_net_pct")
    if bh_net is None:
        nested = coin.get("backtest_buy_hold")
        bh_net = nested.get("net_pct") if isinstance(nested, dict) else None
    try:
        bh = float(bh_net) if bh_net is not None else None
    except (TypeError, ValueError):
        bh = None
    if best is None or bh is None or vs is None:
        return "Best BT net % minus buy-&-hold net % (not the 30d price-gain column)."
    nested = coin.get("backtest_buy_hold")
    bh_tf = str(nested.get("timeframe") or "").strip() if isinstance(nested, dict) else ""
    label = str(coin.get("bot_best_label") or "").strip() or "Best BT"
    bh_label = f"B&H {bh_tf}".strip() if bh_tf else "B&H"
    return f"{label} {best:+.2f}% − {bh_label} {bh:+.2f}% = {vs:+.2f} pp (not 30d price gain)."
