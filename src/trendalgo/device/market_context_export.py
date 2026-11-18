"""Compact Market Context text for PNG export panels (no heavy gfx)."""

from __future__ import annotations

from typing import Any

from trendalgo.device import strings as S
from trendalgo.device.buy_picks import rank_buy_picks
from trendalgo.device.views.market_context_format import (
    levels_lines,
    risk_line,
    signal_line,
    structure_lines,
)


def context_is_ok(ctx: object) -> bool:
    return isinstance(ctx, dict) and bool(ctx.get("ok"))


def coin_context_lines(ctx: dict[str, Any]) -> list[str]:
    """Human lines for one pair's Market Context band."""
    if not context_is_ok(ctx):
        return []
    lines = [S.MARKET_CTX_TITLE, signal_line(ctx)]
    levels = levels_lines(ctx)
    if levels:
        lines.append(S.MARKET_CTX_LEVELS + ": " + " · ".join(levels[:4]))
    lines.append(risk_line(ctx).replace("\n", " · "))
    struct = structure_lines(ctx)
    if struct:
        lines.append(S.MARKET_CTX_STRUCTURE + ": " + " · ".join(struct[:3]))
    return lines


def buy_picks_export_rows(coins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Top Market Context picks for the Qualified share band."""
    return rank_buy_picks(coins)


def buy_pick_cells(pick: dict[str, Any]) -> list[str]:
    score = pick.get("score")
    conf = pick.get("confidence")
    rr = pick.get("rr_r1")
    ta = pick.get("bot_best_net_pct")
    try:
        score_s = f"{float(score):+.2f}" if score is not None else "—"
    except (TypeError, ValueError):
        score_s = "—"
    try:
        conf_s = f"{float(conf):.0f}" if conf is not None else "—"
    except (TypeError, ValueError):
        conf_s = "—"
    try:
        rr_s = f"{float(rr):.2f}" if rr is not None else "—"
    except (TypeError, ValueError):
        rr_s = "—"
    try:
        ta_s = f"{float(ta):+.1f}%" if ta is not None else S.BUY_PICKS_TA_NONE
    except (TypeError, ValueError):
        ta_s = S.BUY_PICKS_TA_NONE
    return [
        str(pick.get("pair") or pick.get("symbol") or "—"),
        str(pick.get("regime") or "—"),
        str(pick.get("signal") or "—"),
        conf_s,
        score_s,
        str(pick.get("nearest_sr") or "—"),
        rr_s,
        str(pick.get("confluence") or "—"),
        ta_s,
    ]
