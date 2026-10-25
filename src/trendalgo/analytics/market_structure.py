"""VWAP, volume profile lite, extension, BTC corr, spread, confluence, nearest S/R."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

EXTENSION_BARS = 90


@dataclass(frozen=True)
class StructureExtras:
    nearest_sr_name: str | None
    nearest_sr_pct: float | None
    nearest_sr_atr: float | None
    confluence: int
    vwap: float | None
    vwap_dist_pct: float | None
    poc: float | None
    vah: float | None
    val: float | None
    drawdown_from_high_pct: float | None
    runup_from_low_pct: float | None
    btc_corr: float | None
    spread_pct: float | None
    volume_ok: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def has_real_volume(volumes: np.ndarray | None) -> bool:
    if volumes is None or len(volumes) == 0:
        return False
    if not np.isfinite(volumes).any():
        return False
    return (
        float(np.nanstd(volumes)) > 1e-12 or float(np.nanmax(volumes) - np.nanmin(volumes)) > 1e-9
    )


def session_vwap(closes: np.ndarray, volumes: np.ndarray, *, bars: int = 48) -> float | None:
    if not has_real_volume(volumes) or len(closes) < 2:
        return None
    n = min(bars, len(closes))
    c = closes[-n:]
    v = volumes[-n:]
    denom = float(np.nansum(v))
    if denom <= 1e-12:
        return None
    return float(np.nansum(c * v) / denom)


def volume_profile_lite(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    *,
    bins: int = 24,
    lookback: int = 96,
) -> tuple[float | None, float | None, float | None]:
    """Return POC, VAH, VAL from a simple volume histogram."""
    if not has_real_volume(volumes) or len(closes) < 8:
        return None, None, None
    n = min(lookback, len(closes))
    hi = float(np.nanmax(highs[-n:]))
    lo = float(np.nanmin(lows[-n:]))
    if not np.isfinite(hi) or not np.isfinite(lo) or hi - lo <= 1e-12:
        return None, None, None
    edges = np.linspace(lo, hi, bins + 1)
    hist = np.zeros(bins, dtype=float)
    for i in range(len(closes) - n, len(closes)):
        price = float(closes[i])
        vol = float(volumes[i]) if np.isfinite(volumes[i]) else 0.0
        idx = int(np.clip(np.searchsorted(edges, price, side="right") - 1, 0, bins - 1))
        hist[idx] += vol
    if hist.sum() <= 0:
        return None, None, None
    poc_i = int(np.argmax(hist))
    poc = float((edges[poc_i] + edges[poc_i + 1]) / 2.0)
    target = 0.70 * float(hist.sum())
    order = list(np.argsort(hist)[::-1])
    covered = 0.0
    selected: set[int] = set()
    for i in order:
        selected.add(int(i))
        covered += float(hist[i])
        if covered >= target:
            break
    lo_i, hi_i = min(selected), max(selected)
    val = float(edges[lo_i])
    vah = float(edges[hi_i + 1])
    return poc, vah, val


def extension_stats(
    closes: np.ndarray, *, bars: int = EXTENSION_BARS
) -> tuple[float | None, float | None]:
    if len(closes) < 3:
        return None, None
    window = closes[-min(bars, len(closes)) :]
    hi = float(np.nanmax(window))
    lo = float(np.nanmin(window))
    last = float(closes[-1])
    dd = 100.0 * (last - hi) / hi if hi > 0 else None
    ru = 100.0 * (last - lo) / lo if lo > 0 else None
    return (round(dd, 3) if dd is not None else None, round(ru, 3) if ru is not None else None)


def corr_vs_btc(closes: np.ndarray, btc_closes: np.ndarray | None) -> float | None:
    if btc_closes is None or len(closes) < 10 or len(btc_closes) < 10:
        return None
    n = min(len(closes), len(btc_closes), 90)
    a = np.diff(np.log(np.clip(closes[-n:], 1e-12, None)))
    b = np.diff(np.log(np.clip(btc_closes[-n:], 1e-12, None)))
    m = min(len(a), len(b))
    if m < 5:
        return None
    a, b = a[-m:], b[-m:]
    if float(np.std(a)) < 1e-12 or float(np.std(b)) < 1e-12:
        return None
    return round(float(np.corrcoef(a, b)[0, 1]), 3)


def spread_pct(bid: float | None, ask: float | None, last: float | None = None) -> float | None:
    try:
        if bid is not None and ask is not None and float(bid) > 0 and float(ask) >= float(bid):
            mid = (float(bid) + float(ask)) / 2.0
            return round(100.0 * (float(ask) - float(bid)) / mid, 4) if mid else None
        if last is not None and bid is not None and float(last) > 0:
            return round(100.0 * abs(float(last) - float(bid)) / float(last), 4)
    except (TypeError, ValueError):
        return None
    return None


def nearest_sr(
    price: float,
    levels: dict[str, float],
    atr: float,
) -> tuple[str | None, float | None, float | None]:
    if not levels or price <= 0:
        return None, None, None
    best_name = None
    best_dist = None
    for name, lvl in levels.items():
        if name == "PP":
            continue
        dist = abs(float(lvl) - price)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_name = name
    if best_name is None or best_dist is None:
        return None, None, None
    pct = 100.0 * best_dist / price
    atr_d = best_dist / atr if atr > 1e-12 else None
    return best_name, round(pct, 3), (round(atr_d, 3) if atr_d is not None else None)


def confluence_count(
    price: float,
    pivot_levels: dict[str, float],
    *,
    fib_levels: list[float] | None = None,
    ema: float | None = None,
    tol_pct: float = 0.004,
) -> int:
    """How many distinct families sit near price (pivot / fib / ema)."""
    count = 0
    if any(abs(price - float(p)) / price <= tol_pct for p in pivot_levels.values() if price > 0):
        count += 1
    if fib_levels and any(
        abs(price - float(f)) / price <= tol_pct for f in fib_levels if price > 0
    ):
        count += 1
    if ema is not None and price > 0 and abs(price - float(ema)) / price <= tol_pct:
        count += 1
    return count


def fib_levels_from_swing(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> list[float]:
    n = len(closes)
    if n < 10:
        return []
    look = min(48, n)
    swing_hi = float(np.nanmax(highs[-look:]))
    swing_lo = float(np.nanmin(lows[-look:]))
    span = swing_hi - swing_lo
    if span <= 1e-12:
        return []
    return [swing_hi - r * span for r in (0.382, 0.5, 0.618)]
