"""Rank Qualified scanner coins by Market Context consensus score (always top 10)."""

from __future__ import annotations

from typing import Any

_TOP_N = 10


def rank_buy_picks(coins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Top ``_TOP_N`` coins by consensus score (any signal). Pure; no I/O."""
    scored: list[dict[str, Any]] = []
    for coin in coins:
        row = _pick_row(coin)
        if row is not None:
            scored.append(row)
    scored.sort(
        key=lambda r: (
            float(r["score"]),
            float(r["bot_best_net_pct"]) if r["bot_best_net_pct"] is not None else float("-inf"),
            float(r["confidence"]),
        ),
        reverse=True,
    )
    return scored[:_TOP_N]


def _pick_row(coin: dict[str, Any]) -> dict[str, Any] | None:
    ctx = coin.get("market_context")
    if not isinstance(ctx, dict) or not ctx.get("ok"):
        return None
    cons = ctx.get("consensus") if isinstance(ctx.get("consensus"), dict) else {}
    signal = str(cons.get("signal") or "Neutral")
    struct = ctx.get("structure") if isinstance(ctx.get("structure"), dict) else {}
    risk = ctx.get("risk") if isinstance(ctx.get("risk"), dict) else {}
    try:
        score = float(cons.get("score") or 0.0)
        confidence = float(cons.get("confidence") or 0.0)
    except (TypeError, ValueError):
        return None
    rr = risk.get("rr_to_r1")
    try:
        rr_f = float(rr) if rr is not None else None
    except (TypeError, ValueError):
        rr_f = None
    best = coin.get("bot_best_net_pct")
    try:
        best_f = float(best) if best is not None else None
    except (TypeError, ValueError):
        best_f = None
    try:
        confluence = int(struct.get("confluence") or 0)
    except (TypeError, ValueError):
        confluence = 0
    return {
        "symbol": str(coin.get("symbol") or "").upper(),
        "pair": str(coin.get("pair") or coin.get("symbol") or "").upper(),
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "nearest_sr": str(struct.get("nearest_sr_name") or "") or None,
        "rr_r1": rr_f,
        "confluence": confluence,
        "regime": str(ctx.get("regime_label") or "") or None,
        "bot_best_net_pct": best_f,
        "bot_best_label": str(coin.get("bot_best_label") or "") or None,
        "fallback": False,
    }
