"""Pick a protective TSL from a 1–20% grid: max net, then lowest plateau + breath."""

from __future__ import annotations

from typing import Any

TSL_BREATH_PCT = 0.01
_NET_EPS = 1e-6


def pick_tsl_from_grid(
    trials: list[dict[str, Any]],
    *,
    signal_net: float | None = None,
) -> dict[str, Any] | None:
    """Most profitable TSL; on a tied plateau, lowest safe +1% breath (cap 20%).

    Never returns a trial with trailing_stop_pct <= 0 when any positive-TSL
    trial exists. ``signal_net`` is the signal-only baseline from Stage B.
    """
    usable = [t for t in trials if int(t.get("trades") or 0) >= 1]
    if not usable:
        return None

    def _net(row: dict[str, Any]) -> float:
        return float(row.get("net_profit") or float("-inf"))

    def _tsl(row: dict[str, Any]) -> float:
        return float(row.get("trailing_stop_pct") or 0.0)

    def _hits(row: dict[str, Any]) -> int:
        return int(row.get("tsl_hits") or 0)

    by_tsl = {_tsl(t): t for t in usable if _tsl(t) > 0}
    if not by_tsl:
        return None

    max_net = max(_net(t) for t in by_tsl.values())
    sig = float(signal_net) if signal_net is not None else None

    if sig is not None and sig > max_net + _NET_EPS:
        plateau_tsls = [
            tsl for tsl, row in by_tsl.items() if _hits(row) == 0 and _net(row) >= sig - _NET_EPS
        ]
        if not plateau_tsls:
            plateau_tsls = [tsl for tsl, row in by_tsl.items() if _hits(row) == 0]
        if not plateau_tsls:
            return max(by_tsl.values(), key=lambda r: (_net(r), -_tsl(r)))
    else:
        plateau_tsls = [tsl for tsl, row in by_tsl.items() if _net(row) >= max_net - _NET_EPS]

    low = min(plateau_tsls)
    breath = min(0.20, round(low + TSL_BREATH_PCT, 4))
    # +1% breath only when that step stays on the equal / unhit plateau.
    chosen_tsl = breath if breath in plateau_tsls else low
    out = dict(by_tsl[chosen_tsl])
    if chosen_tsl != low:
        out["tsl_breath"] = True
    out["protective_tsl"] = True
    return out
