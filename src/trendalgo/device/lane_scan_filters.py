"""TradFi / Forex opportunity-scan filter prefs (move / range / top-N; ADV optional)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from trendalgo.device.profile import read_json, write_json

LaneFilterId = Literal["tradfi", "forex"]

_FILE = "lane_scan_filters.json"
_GAIN_BARS = 22

# Balanced defaults — ADV off; cut flats by move/range then top-N.
DEFAULT_MIN_ADV_USD = 0.0
DEFAULT_MIN_PRICE = 0.0
DEFAULT_MIN_ABS_GAIN_PCT = 5.0
DEFAULT_MIN_RANGE_PCT = 8.0
DEFAULT_TOP_N = 120

# Presets: (min_abs_gain_pct, min_range_pct, top_n). ADV stays 0.
TRADFI_MOVE_PRESETS: dict[str, tuple[float, float, int]] = {
    "wide": (3.0, 5.0, 200),
    "balanced": (5.0, 8.0, 120),
    "tight": (8.0, 12.0, 80),
    "strict": (12.0, 18.0, 50),
}

# Back-compat: old ADV preset map (unused by apply_preset; kept for imports/tests).
TRADFI_ADV_PRESETS: dict[str, float] = {
    "wide": 0.0,
    "balanced": 0.0,
    "tight": 0.0,
    "strict": 0.0,
}
TRADFI_PRESETS: dict[str, tuple[float, int]] = {
    key: (0.0, top_n) for key, (_g, _r, top_n) in TRADFI_MOVE_PRESETS.items()
}


@dataclass(frozen=True)
class LaneScanFilters:
    min_adv_usd: float = DEFAULT_MIN_ADV_USD
    min_price: float = DEFAULT_MIN_PRICE
    min_abs_gain_pct: float = DEFAULT_MIN_ABS_GAIN_PCT
    min_range_pct: float = DEFAULT_MIN_RANGE_PCT
    top_n: int = DEFAULT_TOP_N

    def clamped(self, *, lane: LaneFilterId = "tradfi") -> LaneScanFilters:
        adv = max(0.0, float(self.min_adv_usd))
        price = max(0.0, float(self.min_price))
        gain = max(0.0, float(self.min_abs_gain_pct))
        rng = max(0.0, float(self.min_range_pct))
        top = max(0, int(self.top_n))
        if lane == "forex":
            return LaneScanFilters(0.0, 0.0, 0.0, 0.0, 0)
        return LaneScanFilters(adv, price, gain, rng, top)


def default_lane_scan_filters(lane: LaneFilterId = "tradfi") -> LaneScanFilters:
    if lane == "forex":
        return LaneScanFilters(0.0, 0.0, 0.0, 0.0, 0)
    return LaneScanFilters()


def apply_preset(lane: LaneFilterId, preset: str, current: LaneScanFilters) -> LaneScanFilters:
    key = (preset or "balanced").strip().lower()
    if lane == "forex":
        return LaneScanFilters(0.0, 0.0, 0.0, 0.0, 0)
    gain, rng, top = TRADFI_MOVE_PRESETS.get(key, TRADFI_MOVE_PRESETS["balanced"])
    return LaneScanFilters(
        min_adv_usd=0.0,
        min_price=current.min_price,
        min_abs_gain_pct=gain,
        min_range_pct=rng,
        top_n=top,
    )


def load_lane_scan_filters(root: Path, lane: LaneFilterId) -> LaneScanFilters:
    raw = read_json(root / _FILE)
    if not isinstance(raw, dict):
        return default_lane_scan_filters(lane)
    block = raw.get(lane)
    if not isinstance(block, dict):
        return default_lane_scan_filters(lane)
    return LaneScanFilters(
        min_adv_usd=float(block.get("min_adv_usd", DEFAULT_MIN_ADV_USD) or 0),
        min_price=float(block.get("min_price", DEFAULT_MIN_PRICE) or 0),
        min_abs_gain_pct=float(block.get("min_abs_gain_pct", DEFAULT_MIN_ABS_GAIN_PCT) or 0),
        min_range_pct=float(block.get("min_range_pct", DEFAULT_MIN_RANGE_PCT) or 0),
        top_n=int(block.get("top_n", DEFAULT_TOP_N) or 0),
    ).clamped(lane=lane)


def save_lane_scan_filters(root: Path, lane: LaneFilterId, prefs: LaneScanFilters) -> None:
    path = root / _FILE
    prior = read_json(path)
    payload: dict[str, Any] = dict(prior) if isinstance(prior, dict) else {}
    clipped = prefs.clamped(lane=lane)
    payload[lane] = {
        "min_adv_usd": clipped.min_adv_usd,
        "min_price": clipped.min_price,
        "min_abs_gain_pct": clipped.min_abs_gain_pct,
        "min_range_pct": clipped.min_range_pct,
        "top_n": clipped.top_n,
    }
    write_json(path, payload)


def avg_dollar_volume(points: list[Any], *, lookback: int = 20) -> float:
    """Mean of close*volume over the last ``lookback`` bars."""
    if not points:
        return 0.0
    window = points[-lookback:] if len(points) >= lookback else points
    total = 0.0
    n = 0
    for p in window:
        try:
            close = float(p.close)
            vol = float(p.volume)
        except (TypeError, ValueError, AttributeError):
            continue
        if close <= 0:
            continue
        total += close * max(0.0, vol)
        n += 1
    return total / n if n else 0.0


def last_close(points: list[Any]) -> float:
    if not points:
        return 0.0
    try:
        return float(points[-1].close)
    except (TypeError, ValueError, AttributeError):
        return 0.0


def abs_gain_pct(points: list[Any], *, lookback: int = _GAIN_BARS) -> float:
    """Absolute close-to-close % move over ``lookback`` sessions (0–100 scale)."""
    if len(points) < 2:
        return 0.0
    window = points[-lookback:] if len(points) >= lookback else points
    try:
        first = float(window[0].close)
        last = float(window[-1].close)
    except (TypeError, ValueError, AttributeError):
        return 0.0
    if first <= 0:
        return 0.0
    return abs((last / first) - 1.0) * 100.0


def realized_range_pct(points: list[Any], *, lookback: int = _GAIN_BARS) -> float:
    """(max high − min low) / mid × 100 over ``lookback`` sessions."""
    if not points:
        return 0.0
    window = points[-lookback:] if len(points) >= lookback else points
    highs: list[float] = []
    lows: list[float] = []
    for p in window:
        try:
            highs.append(float(p.high))
            lows.append(float(p.low))
        except (TypeError, ValueError, AttributeError):
            continue
    if not highs or not lows:
        return 0.0
    hi = max(highs)
    lo = min(lows)
    mid = (hi + lo) / 2.0
    if mid <= 0:
        return 0.0
    return ((hi - lo) / mid) * 100.0
