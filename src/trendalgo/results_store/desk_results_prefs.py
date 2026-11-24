"""Backtest / results view prefs apply (AV-G-OTH2)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from trendalgo.device.results_view_prefs import load_results_prefs, save_results_prefs

__all__ = ["apply_results_prefs"]


def apply_results_prefs(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    cur = load_results_prefs(root)
    prefs = replace(
        cur,
        perfect_only=bool(payload.get("perfect_only", cur.perfect_only)),
        heatmap_enabled=bool(payload.get("heatmap_enabled", cur.heatmap_enabled)),
        market_context_collapsed=bool(
            payload.get("market_context_collapsed", cur.market_context_collapsed)
        ),
        last_pair=str(payload.get("last_pair") or cur.last_pair).strip().upper() or cur.last_pair,
    )
    save_results_prefs(root, prefs)
    return {
        "ok": True,
        "perfect_only": prefs.perfect_only,
        "heatmap_enabled": prefs.heatmap_enabled,
        "market_context_collapsed": prefs.market_context_collapsed,
        "last_pair": prefs.last_pair,
    }
