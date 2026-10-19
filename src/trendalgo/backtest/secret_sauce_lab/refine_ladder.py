"""Soft refine accept ladder + peer TF helpers."""

from __future__ import annotations

from typing import Any

_DENSE_TFS = ("1h", "2h", "3h", "4h")


def ladder_accepts(
    net: float,
    prior_net: float,
    peer_usd: float | None,
    bh_usd: float | None,
    same_tf_as_prior: bool = True,
) -> bool:
    """Ship if clears absolute peer (#2) or beats max(prior, B&H)."""
    if peer_usd is not None and net > peer_usd + 1e-9:
        return True
    floor = prior_net
    if bh_usd is not None:
        floor = max(floor, bh_usd)
    if net > floor + 1e-9:
        return True
    del same_tf_as_prior  # kept for call-site clarity
    return False


def peer_tf_for_indicator(rows: list[dict[str, Any]], indicator: str) -> str | None:
    best_tf = None
    best_net = float("-inf")
    for r in rows:
        if str(r.get("indicator") or "") != indicator:
            continue
        net = float(r.get("net_pct") or float("-inf"))
        if net > best_net:
            best_net = net
            best_tf = str(r.get("timeframe") or "") or None
    return best_tf


def refine_tf_candidates(peer_tf: str | None, sauce_tf: str) -> list[str]:
    """Peer TF first, then densest 1h–4h, then sauce TF."""
    out: list[str] = []
    for t in (peer_tf, *_DENSE_TFS, sauce_tf):
        if t and t not in out:
            out.append(t)
    return out


def refine_tf_budgets(n_tf: int, time_budget_s: float) -> list[float]:
    """Peer TF gets a plurality; remaining TFs share the rest (keep hunting Oracle gap)."""
    n = max(1, n_tf)
    if n == 1:
        return [time_budget_s]
    # 50% peer TF, rest split evenly — peer clear first, then Oracle hunt.
    head = time_budget_s * 0.50
    rest = (time_budget_s - head) / (n - 1)
    return [head] + [rest] * (n - 1)
