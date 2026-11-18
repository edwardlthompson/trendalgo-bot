"""Portfolio sync + period benchmark attribution by venue (S22, BILL-02)."""

from __future__ import annotations

import json
from typing import Any


def attribution_by_venue(sync_results: dict[str, Any]) -> dict[str, float]:
    """Roll up synced portfolio USD totals per venue for billing reports."""
    totals: dict[str, float] = {}
    for result in sync_results.values():
        if not isinstance(result, dict) or result.get("skipped") or "total_usd" not in result:
            continue
        venue = str(result.get("venue") or "unknown")
        totals[venue] = round(totals.get(venue, 0.0) + float(result.get("total_usd", 0)), 2)
    return totals


def _bh_for_fill(fill: dict[str, Any]) -> float:
    stake = float(fill.get("stake_usd") or 0)
    open_px = float(fill.get("period_open_px") or 0)
    close_px = float(fill.get("period_close_px") or 0)
    if stake <= 0 or open_px <= 0:
        return 0.0
    return round(stake * ((close_px / open_px) - 1.0), 2)


def benchmark_refs_from_fills(fills: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-instrument B&H refs from venue fills at the stake the bot used."""
    refs: dict[str, dict[str, Any]] = {}
    for fill in fills:
        pair = str(fill.get("pair") or "unknown")
        bh = _bh_for_fill(fill)
        prior = refs.get(pair)
        if prior is None:
            refs[pair] = {
                "pair": pair,
                "stake_usd": float(fill.get("stake_usd") or 0),
                "period_open_px": float(fill.get("period_open_px") or 0),
                "period_close_px": float(fill.get("period_close_px") or 0),
                "bh_net_usd": bh,
                "venue": str(fill.get("venue") or "unknown"),
                "fill_ts": str(fill.get("fill_ts") or ""),
            }
            continue
        # Same instrument: sum stake-weighted B&H; keep latest close stamp.
        prior["bh_net_usd"] = round(float(prior["bh_net_usd"]) + bh, 2)
        prior["stake_usd"] = round(float(prior["stake_usd"]) + float(fill.get("stake_usd") or 0), 2)
        prior["period_close_px"] = float(fill.get("period_close_px") or prior["period_close_px"])
        prior["fill_ts"] = str(fill.get("fill_ts") or prior["fill_ts"])
    return refs


def pin_benchmark_refs(refs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Pin open/close venue mids so statements never re-query the venue."""
    pinned: dict[str, dict[str, Any]] = {}
    for pair, raw in refs.items():
        pinned[pair] = {
            **raw,
            "venue_mid_open": float(raw.get("period_open_px") or raw.get("venue_mid_open") or 0),
            "venue_mid_close": float(raw.get("period_close_px") or raw.get("venue_mid_close") or 0),
            "pinned": True,
        }
    return pinned


def sum_bh_net(refs: dict[str, dict[str, Any]]) -> float:
    return round(sum(float(r.get("bh_net_usd") or 0) for r in refs.values()), 2)


def dumps_benchmark_refs(refs: dict[str, dict[str, Any]]) -> str:
    return json.dumps(refs, sort_keys=True)


def loads_benchmark_refs(raw: str | None) -> dict[str, dict[str, Any]]:
    if not raw:
        return {}
    data = json.loads(raw)
    return {str(k): dict(v) for k, v in data.items()} if isinstance(data, dict) else {}
