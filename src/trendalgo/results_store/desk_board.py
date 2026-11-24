"""Desk board mutations: watchlist, buy picks, create-bot, progress (gap depth)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.buy_picks import rank_buy_picks
from trendalgo.device.lts_scan_model import load_lts_rows, load_watchlist, save_watchlist
from trendalgo.device.plan_model import (
    STAKE_FIXED,
    check_plan,
    load_plan,
    plan_document,
    validate_bot,
)
from trendalgo.device.profile import PLAN_FILE, ProfileError, read_json, write_json


def toggle_watch(root: Path, pair: str, *, lane: str = "crypto") -> dict[str, Any]:
    needle = str(pair or "").strip().upper()
    if not needle:
        raise ValueError("pair required")
    current = [str(p).strip().upper() for p in load_watchlist(root, lane=lane) if str(p).strip()]
    if needle in current:
        current = [p for p in current if p != needle]
        watched = False
    else:
        current.append(needle)
        watched = True
    save_watchlist(root, current, lane=lane)
    return {"pair": needle, "watched": watched, "count": len(current)}


def load_buy_picks_surface(root: Path, *, lane: str = "crypto") -> dict[str, Any]:
    coins = load_lts_rows(root, lane=lane)
    picks = rank_buy_picks(coins)
    return {"lane": lane, "rows": picks, "count": len(picks)}


def load_progress_surface(root: Path, *, lane: str = "crypto") -> dict[str, Any]:
    from trendalgo.results_store.desk_progress import load_progress_surface as _load

    return _load(root, lane=lane)


def create_bot_from_fields(
    root: Path,
    *,
    pair: str,
    indicator: str,
    timeframe: str = "1h",
    name: str = "",
    stake_usd: float = 25.0,
) -> dict[str, Any]:
    pair_u = str(pair or "").strip().upper()
    ind = str(indicator or "").strip()
    if not pair_u or "/" not in pair_u:
        raise ValueError("pair required like BTC/USD")
    if not ind:
        raise ValueError("indicator required")
    bot_name = str(name or "").strip() or f"{pair_u.split('/')[0]}-{ind}"[:40]
    spec, errors = validate_bot(
        name=bot_name,
        pair=pair_u,
        timeframe=str(timeframe or "1h"),
        indicator=ind,
        stake=str(stake_usd),
        trailing_stop="2",
        stake_mode=STAKE_FIXED,
    )
    if spec is None or errors:
        raise ValueError("; ".join(errors) or "invalid bot")
    try:
        version, bots = load_plan(read_json(root / PLAN_FILE))
    except ProfileError:
        version, bots = 0, []
    clashes = check_plan([*bots, spec])
    if clashes:
        raise ValueError("; ".join(clashes))
    bots = [*bots, spec]
    write_json(root / PLAN_FILE, plan_document(max(version, 1), bots))
    return {
        "ok": True,
        "name": spec.name,
        "pair": spec.pair,
        "indicator": spec.indicator,
        "count": len(bots),
    }
