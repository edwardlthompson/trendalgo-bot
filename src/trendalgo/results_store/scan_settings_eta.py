"""Lane ETA payload for Avalonia Scan Settings (AV-G-TF2)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from trendalgo.backtest.heartbeat_tf import needs_1m_base
from trendalgo.device.lane_prefs import load_lane_prefs
from trendalgo.device.lts_scan_model import load_filters
from trendalgo.device.scan_bt_prefs import (
    ScanBtPrefs,
    enabled_strategies,
    load_scan_bt_prefs,
    selected_timeframes,
)
from trendalgo.device.scan_eta_filters import META_FUNNEL, projected_scan_coins
from trendalgo.device.scan_time_history import (
    ScanTimeHistory,
    estimate_label,
    estimate_scan_seconds,
    load_history,
)


def _fmt_duration(seconds: float) -> str:
    s = max(0.0, float(seconds))
    if s < 90:
        return f"{s:.0f}s"
    if s < 3600:
        return f"{s / 60:.1f}m"
    return f"{s / 3600:.1f}h"


def _crypto_n(root: Path) -> int:
    saved = load_filters(root, lane="crypto")
    funnel = saved.get(META_FUNNEL) if isinstance(saved.get(META_FUNNEL), dict) else None
    try:
        min_vol = float(saved.get("min_volume_usd") or saved.get("min_volume") or 100_000.0)
    except (TypeError, ValueError):
        min_vol = 100_000.0
    req_1h = bool(saved.get("require_continuous_1h", True)) if isinstance(saved, dict) else True
    return projected_scan_coins(
        funnel,
        min_volume_usd=min_vol,
        require_continuous_1h=req_1h,
        fallback_n=40,
    )


def _load_benchmark_lane_histories(
    root: Path,
    base_hist: ScanTimeHistory,
) -> tuple[dict[str, ScanTimeHistory], str]:
    """Build per-lane ScanTimeHistory from benchmark_last_results.json when available."""
    path = root / "benchmark_last_results.json"
    if not path.is_file():
        return {}, ""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, ""
    if not isinstance(raw, dict) or not raw.get("ok"):
        return {}, ""
    n_strat = max(1, int(raw.get("strategies_count") or 1))
    n_tf = max(1, int(raw.get("timeframes_count") or 1))
    combos = max(1, n_strat * n_tf)
    ran_at = str(raw.get("ran_at") or "")
    out: dict[str, ScanTimeHistory] = {}
    for asset in raw.get("assets") or []:
        if not isinstance(asset, dict) or asset.get("status") != "ok":
            continue
        lane = str(asset.get("lane") or "").strip()
        if not lane:
            continue
        load_s = max(0.05, float(asset.get("load_s") or 0.0))
        work_s = max(0.05, float(asset.get("pass1_s") or 0.0) + float(asset.get("deepen_s") or 0.0))
        mc_s = max(0.01, float(asset.get("mc_s") or base_hist.mean_mc_s))
        sauce_s = max(0.05, float(asset.get("sauce_s") or base_hist.mean_sauce_s))
        # Account for multi-coin thread sharing on 8 concurrent coins vs 1-coin benchmark.
        per_combo = (work_s * 1.20) / combos
        out[lane] = ScanTimeHistory(
            samples=[],
            mean_load_1h_s=load_s,
            mean_load_1m_s=base_hist.mean_load_1m_s,
            mean_per_strat_tf_s=per_combo,
            mean_mc_s=mc_s,
            mean_sauce_s=sauce_s,
        )
    return out, ran_at


def scan_settings_eta(root: Path, prefs: ScanBtPrefs | None = None) -> dict[str, Any]:
    """Per-lane ETA lines using timing history + benchmark calibration."""
    bt: ScanBtPrefs = prefs if prefs is not None else load_scan_bt_prefs(root)
    tfs = list(selected_timeframes(bt, root=root))
    n_tf = max(1, len(tfs))
    n_strat = max(1, len(enabled_strategies(bt.strategy_denylist)))
    had_sub = needs_1m_base(tfs)
    hist = load_history(root)
    bench_lanes, bench_ran_at = _load_benchmark_lane_histories(root, hist)
    lane = load_lane_prefs(root)
    try:
        from trendalgo.device.lane_scan_filters import load_lane_scan_filters

        top = load_lane_scan_filters(root, "tradfi").top_n
        tradfi_n = max(1, int(top)) if top and int(top) > 0 else 40
    except Exception:  # noqa: BLE001
        tradfi_n = 40
    lanes = [
        ("Crypto", _crypto_n(root), bool(lane.auto_scan_crypto), 2.0),
        ("TradFi", tradfi_n, bool(lane.auto_scan_tradfi), 35.0),
        ("Forex", 20, bool(lane.auto_scan_forex), 2.0),
    ]
    lines: list[str] = []
    lanes_cal: dict[str, dict[str, float]] = {}
    grand = 0.0
    for name, n_coins, auto_on, overhead_s in lanes:
        l_hist = bench_lanes.get(name, hist)
        lanes_cal[name] = {
            "mean_load_1h_s": round(float(l_hist.mean_load_1h_s), 4),
            "mean_load_1m_s": round(float(l_hist.mean_load_1m_s), 4),
            "mean_per_strat_tf_s": round(float(l_hist.mean_per_strat_tf_s), 6),
            "mean_mc_s": round(float(l_hist.mean_mc_s), 4),
            "mean_sauce_s": round(float(l_hist.mean_sauce_s), 4),
            "bars_overhead_s": overhead_s,
        }
        label = estimate_label(
            l_hist,
            n_strategies=n_strat,
            n_timeframes=n_tf,
            had_subhour=had_sub,
            n_coins=n_coins,
            market_context=bool(bt.market_context_with_scan),
            sauce_with_scan=bool(bt.sauce_with_scan),
            sauce_top_n=int(bt.sauce_top_n),
        )
        _c, _m, _s, total = estimate_scan_seconds(
            l_hist,
            n_strategies=n_strat,
            n_timeframes=n_tf,
            had_subhour=had_sub,
            n_coins=n_coins,
            market_context=bool(bt.market_context_with_scan),
            sauce_with_scan=bool(bt.sauce_with_scan),
            sauce_top_n=int(bt.sauce_top_n),
        )
        lines.append(f"{name}: {label}")
        if auto_on:
            grand += total + overhead_s
    saved = load_filters(root, lane="crypto")
    try:
        interval_minutes = max(15, int(saved.get("interval_minutes") or 60))
    except (TypeError, ValueError):
        interval_minutes = 60
    overrun = grand > (interval_minutes * 60.0 * 0.85)
    recommended = min(
        1440,
        max(15, int(math.ceil((grand / 60.0) * 1.25 / 15.0) * 15)),
    )
    overrun_warning = (
        f"Estimated auto-scan (~{_fmt_duration(grand)}) risks overlapping your "
        f"{interval_minutes}m schedule. Raise interval to {recommended}m or reduce timeframes/strategies."
        if overrun
        else ""
    )
    funnel = saved.get(META_FUNNEL) if isinstance(saved.get(META_FUNNEL), dict) else None
    return {
        "title": "Estimated scan time",
        "lines": lines,
        "total": f"Grand total (auto-scan on): ~{_fmt_duration(grand)}",
        "note": "TF/FX ≈ bars + All-TA on every pair that passes desk filters.",
        "grand_seconds": round(grand, 1),
        "interval_minutes": interval_minutes,
        "overrun": overrun,
        "recommended_interval_minutes": recommended,
        "overrun_warning": overrun_warning,
        "calibration": {
            "mean_load_1h_s": round(float(hist.mean_load_1h_s), 4),
            "mean_load_1m_s": round(float(hist.mean_load_1m_s), 4),
            "mean_per_strat_tf_s": round(float(hist.mean_per_strat_tf_s), 6),
            "mean_mc_s": round(float(hist.mean_mc_s), 4),
            "mean_sauce_s": round(float(hist.mean_sauce_s), 4),
            "crypto_coins": lanes[0][1],
            "tradfi_coins": lanes[1][1],
            "forex_coins": lanes[2][1],
            "funnel": funnel,
            "benchmark_ran_at": bench_ran_at,
            "lanes_calibration": lanes_cal,
        },
    }
