"""Lane prefs + TradFi scan filters + results-view for Avalonia Scan Settings."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from trendalgo.device.lane_prefs import LanePrefs, load_lane_prefs, save_lane_prefs
from trendalgo.device.lane_scan_filters import (
    TRADFI_MOVE_PRESETS,
    LaneScanFilters,
    apply_preset,
    load_lane_scan_filters,
    save_lane_scan_filters,
)
from trendalgo.device.results_view_prefs import (
    ResultsViewPrefs,
    load_results_prefs,
    save_results_prefs,
)


def lane_settings_view(root: Path) -> dict[str, Any]:
    prefs = load_lane_prefs(root)
    tradfi = load_lane_scan_filters(root, "tradfi")
    results = load_results_prefs(root)
    return {
        "lane_prefs": {
            "auto_scan_crypto": prefs.auto_scan_crypto,
            "auto_scan_tradfi": prefs.auto_scan_tradfi,
            "auto_scan_forex": prefs.auto_scan_forex,
        },
        "lane_scan_filters": {
            "tradfi": asdict(tradfi),
            "presets": {
                key: {
                    "min_abs_gain_pct": gain,
                    "min_range_pct": rng,
                    "top_n": top,
                }
                for key, (gain, rng, top) in TRADFI_MOVE_PRESETS.items()
            },
        },
        "results_view": {
            "heatmap_enabled": results.heatmap_enabled,
            "perfect_only": results.perfect_only,
        },
    }


def apply_lane_settings(root: Path, payload: dict[str, Any]) -> None:
    raw_prefs = payload.get("lane_prefs")
    if isinstance(raw_prefs, dict):
        lane_cur = load_lane_prefs(root)
        save_lane_prefs(
            root,
            LanePrefs(
                auto_scan_crypto=bool(raw_prefs.get("auto_scan_crypto", lane_cur.auto_scan_crypto)),
                auto_scan_tradfi=bool(raw_prefs.get("auto_scan_tradfi", lane_cur.auto_scan_tradfi)),
                auto_scan_forex=bool(raw_prefs.get("auto_scan_forex", lane_cur.auto_scan_forex)),
            ),
        )

    filters = payload.get("lane_scan_filters")
    if isinstance(filters, dict):
        block = filters.get("tradfi")
        if isinstance(block, dict):
            preset = str(block.get("preset") or "").strip().lower()
            filter_cur = load_lane_scan_filters(root, "tradfi")
            nxt = LaneScanFilters(
                min_adv_usd=float(block.get("min_adv_usd", filter_cur.min_adv_usd) or 0),
                min_price=float(block.get("min_price", filter_cur.min_price) or 0),
                min_abs_gain_pct=float(
                    block.get("min_abs_gain_pct", filter_cur.min_abs_gain_pct) or 0
                ),
                min_range_pct=float(block.get("min_range_pct", filter_cur.min_range_pct) or 0),
                top_n=int(block.get("top_n", filter_cur.top_n) or 0),
            )
            if preset:
                nxt = apply_preset("tradfi", preset, nxt)
            save_lane_scan_filters(root, "tradfi", nxt)

    results = payload.get("results_view")
    if isinstance(results, dict):
        view_cur = load_results_prefs(root)
        save_results_prefs(
            root,
            ResultsViewPrefs(
                heatmap_enabled=bool(results.get("heatmap_enabled", view_cur.heatmap_enabled)),
                perfect_only=bool(results.get("perfect_only", view_cur.perfect_only)),
                last_pair=view_cur.last_pair,
                results_dialog_width=view_cur.results_dialog_width,
                results_dialog_height=view_cur.results_dialog_height,
                results_dialog_maximized=view_cur.results_dialog_maximized,
                market_context_collapsed=view_cur.market_context_collapsed,
                buy_picks_collapsed=view_cur.buy_picks_collapsed,
            ),
        )
