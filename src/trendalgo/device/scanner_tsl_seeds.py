"""Select Stage-B signal winners that qualify for the TSL deepen stage."""

from __future__ import annotations

from typing import Any

MIN_TSL_SEED_TRADES = 3


def best_signal_per_strategy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One fleet row per strategy_id — best signal-only net_profit (then trades)."""
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        sid = str(row.get("strategy_id") or "").strip()
        if not sid or sid.upper() == "B&H":
            continue
        prev = best.get(sid)
        if prev is None or _fleet_beats(row, prev):
            best[sid] = row
    return list(best.values())


def select_tsl_seeds(
    rows: list[dict[str, Any]],
    *,
    min_trades: int = MIN_TSL_SEED_TRADES,
) -> list[dict[str, Any]]:
    """Stage-B winners with enough trades to justify a TSL grid."""
    floor = max(1, int(min_trades))
    seeds = [r for r in rows if int(r.get("trades") or 0) >= floor]
    return sorted(seeds, key=lambda r: float(r.get("net_profit") or 0.0), reverse=True)


def _fleet_beats(candidate: dict[str, Any], incumbent: dict[str, Any]) -> bool:
    c_net = float(candidate.get("net_profit") or float("-inf"))
    i_net = float(incumbent.get("net_profit") or float("-inf"))
    if c_net != i_net:
        return c_net > i_net
    return int(candidate.get("trades") or 0) > int(incumbent.get("trades") or 0)
