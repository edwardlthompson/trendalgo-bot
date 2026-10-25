"""Causal pivot / VWAP / POC features for Secret Sauce Lab (sparse keys)."""

from __future__ import annotations

import numpy as np

from trendalgo.analytics.classic_pivots import classic_levels, prior_period_hlc
from trendalgo.analytics.market_structure import has_real_volume, session_vwap, volume_profile_lite

PIVOT_KEYS = (
    "pivot_dist_pp",
    "pivot_dist_s1",
    "pivot_dist_r1",
    "pivot_touch_s1",
    "level_confluence",
    "vwap_dist",
    "poc_dist",
    "inside_va",
)


def merge_pivot_features_into_rows(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    rows: list[dict[str, float]],
    volumes: np.ndarray | None = None,
) -> None:
    """Add causal pivot/VWAP/POC distances (bars ≤ i only). Cap search sparsity."""
    n = len(rows)
    if n == 0 or len(closes) != n:
        return
    vol_ok = has_real_volume(volumes) if volumes is not None else False
    for i, row in enumerate(rows):
        for key in PIVOT_KEYS:
            row[key] = 0.0
        hlc = prior_period_hlc(highs[: i + 1], lows[: i + 1], closes[: i + 1], period_bars=24)
        c = float(closes[i])
        if hlc is None or c <= 0:
            continue
        levels = classic_levels(*hlc)
        span = max(abs(levels["R1"] - levels["S1"]), 1e-12)
        row["pivot_dist_pp"] = (c - levels["PP"]) / span
        row["pivot_dist_s1"] = (c - levels["S1"]) / span
        row["pivot_dist_r1"] = (c - levels["R1"]) / span
        row["pivot_touch_s1"] = 1.0 if abs(c - levels["S1"]) / c <= 0.002 else 0.0
        near_pivot = any(abs(c - float(p)) / c <= 0.004 for p in levels.values())
        # Fib-lite confluence: mid of recent swing
        look = min(48, i + 1)
        swing_hi = float(np.nanmax(highs[i + 1 - look : i + 1]))
        swing_lo = float(np.nanmin(lows[i + 1 - look : i + 1]))
        mid = (swing_hi + swing_lo) / 2.0
        near_fib = abs(c - mid) / c <= 0.004 if c else False
        row["level_confluence"] = float(int(near_pivot) + int(near_fib))

        if vol_ok and volumes is not None:
            vwap = session_vwap(closes[: i + 1], volumes[: i + 1], bars=min(48, i + 1))
            if vwap and vwap > 0:
                row["vwap_dist"] = (c - vwap) / vwap
            poc, vah, val = volume_profile_lite(
                highs[: i + 1],
                lows[: i + 1],
                closes[: i + 1],
                volumes[: i + 1],
                lookback=min(96, i + 1),
            )
            if poc and poc > 0:
                row["poc_dist"] = (c - poc) / poc
            if vah is not None and val is not None and val <= c <= vah:
                row["inside_va"] = 1.0
