"""Fee drag / exposure / excess-vs-hold metrics (SIM-07)."""

from __future__ import annotations

from typing import Any


_FEE_DRAG_REJECT = 0.35


def enrich_trial_stats(
    stats: dict[str, Any],
    *,
    stake_usd: float,
    bh_net: float | None,
    n_bars: int,
) -> dict[str, Any]:
    """Attach honesty columns; set reject_reason when fee drag too high."""
    gross = float(stats.get("gross_profit") or 0.0)
    fees = float(stats.get("fees_paid") or 0.0)
    net = float(stats.get("net_profit") or 0.0)
    trades = int(stats.get("trades") or 0)
    # Gross profit for drag: use positive gross only; if gross<=0 drag is undefined → 1.0
    if gross > 0:
        fee_drag = fees / gross
    else:
        fee_drag = 1.0 if fees > 0 else 0.0
    # Exposure: closed+open trades vs bars (coarse proxy when trade_list absent).
    exposure = min(1.0, (2.0 * trades) / max(1, n_bars))
    excess = None if bh_net is None else net - float(bh_net)
    out = {
        **stats,
        "fee_drag_pct": round(fee_drag, 4),
        "exposure_pct": round(exposure * 100.0, 2),
        "excess_vs_bh": None if excess is None else round(excess, 4),
        "net_pct": round((net / stake_usd) * 100.0, 4) if stake_usd else 0.0,
        "reject_reason": None,
    }
    if fee_drag > _FEE_DRAG_REJECT:
        out["reject_reason"] = f"fee_drag:{fee_drag:.2f}"
    if trades < 1:
        out["reject_reason"] = "min_trades"
    return out
