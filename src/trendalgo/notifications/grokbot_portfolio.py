"""Optional daily portfolio_snapshot webhook. No keys or account identifiers."""

from __future__ import annotations

import os
from typing import Any

from trendalgo.notifications.grokbot_payload import envelope

_TRUE = frozenset({"1", "true", "yes", "on"})
_IDLE = frozenset({"USDT", "USDC", "USD", "DAI", "BUSD", "TUSD", "EUR", "GBP", "USDP", "GUSD"})


def snapshot_enabled() -> bool:
    return os.environ.get("PORTFOLIO_SNAPSHOT_WEBHOOK", "0").strip().lower() in _TRUE


def qualified_bases(coins: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for coin in coins:
        raw = str(coin.get("symbol") or coin.get("pair") or "")
        if not raw:
            continue
        out.add(raw.upper())
        out.add(raw.upper().split("/")[0].split("-")[0])
    return out


def asset_qualified(asset: str, qualified: set[str]) -> bool:
    sym = (asset or "").upper().split("/")[0].split("-")[0]
    return bool(sym) and (sym in qualified or asset.upper() in qualified)


def snapshot_digest(overview: dict[str, Any], qualified: set[str] | None = None) -> dict[str, Any]:
    qualified = qualified or set()
    holdings = [h for h in (overview.get("holdings") or []) if isinstance(h, dict)]
    allocation = [r for r in (overview.get("allocation") or []) if isinstance(r, dict)]
    total = float(overview.get("net_worth_usd") or 0)
    rows: list[dict[str, Any]] = []
    idle = 0.0
    left: list[str] = []
    for row in holdings:
        asset = str(row.get("asset") or "")
        value = float(row.get("value_usd") or 0)
        pct = (value / total) if total else 0.0
        rows.append({"asset": asset, "pct": round(pct, 4)})
        idle_cash = (asset or "").upper().split("/")[0].split("-")[0] in _IDLE
        if idle_cash:
            idle += pct
        elif asset and qualified and not asset_qualified(asset, qualified):
            left.append(asset)
    alloc = [
        {"asset": str(r.get("asset") or ""), "pct": _pct(r)} for r in allocation if r.get("asset")
    ] or rows
    alloc = sorted(alloc, key=_pct, reverse=True)[:12]
    top = alloc[0] if alloc else {"asset": None, "pct": 0.0}
    hhi = round(sum(_pct(r) ** 2 for r in alloc), 4)
    return {
        "allocations": alloc,
        "concentration": {
            "top_asset": top.get("asset"),
            "top_pct": top.get("pct"),
            "hhi": hhi,
        },
        "left_qualified": left[:12],
        "idle_stable_share": round(idle, 4),
        "holding_count": len(holdings),
    }


def maybe_emit_snapshot(overview: dict[str, Any]) -> dict[str, Any] | None:
    if not snapshot_enabled():
        return None
    from trendalgo.lts_vendor.public_snapshot import load_public_snapshot
    from trendalgo.notifications.grokbot import emit

    coins = load_public_snapshot().get("coins") or []
    qualified = qualified_bases([c for c in coins if isinstance(c, dict)])
    digest = snapshot_digest(overview, qualified)
    reason = (
        f"Portfolio snapshot holdings={digest['holding_count']} "
        f"idle_stable={digest['idle_stable_share']:.0%} "
        f"top={digest['concentration']['top_asset']}"
    )
    payload = envelope(event_type="portfolio_snapshot", reason=reason)
    payload["gains"] = digest
    return emit(payload)


def _pct(row: dict[str, Any]) -> float:
    raw = row.get("pct") or 0
    if isinstance(raw, bool):
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw))
    except ValueError:
        return 0.0
