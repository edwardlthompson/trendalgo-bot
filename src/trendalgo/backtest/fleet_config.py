"""Fleet backtest window — same wall-clock period for every timeframe (apples-to-apples)."""

from __future__ import annotations

import os

FLEET_LOOKBACK_DAYS = int(os.environ.get("TRENDALGO_FLEET_LOOKBACK_DAYS", "30"))
FLEET_LOOKBACK_SECONDS = FLEET_LOOKBACK_DAYS * 86_400
OPTIMIZE_TOP_N = int(os.environ.get("TRENDALGO_FLEET_OPTIMIZE_TOP", "10"))
OPTIMIZE_MAX_VARIANTS = int(os.environ.get("TRENDALGO_FLEET_OPT_VARIANTS", "27"))
# Pass 1 & 2 use signal exits only; pass 3 sweeps TSL 0–20% in 2% steps.
PASS12_TRAILING_STOP_PCT = 0.0
DEFAULT_TRAILING_STOP_PCT = PASS12_TRAILING_STOP_PCT
TSL_SWEEP_PCTS: tuple[float, ...] = tuple(i / 100.0 for i in range(0, 21, 2))


def fleet_lookback_seconds(_tv_interval: str = "") -> int:
    """Identical calendar window for all intervals (1S through 1W)."""
    return FLEET_LOOKBACK_SECONDS
