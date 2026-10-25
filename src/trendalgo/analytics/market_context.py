"""Pair-level MarketContext aggregate for Backtest / Scanner panes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from trendalgo.analytics.classic_pivots import compute_pivot_set
from trendalgo.analytics.indicator_consensus import ConsensusResult, compute_consensus
from trendalgo.analytics.market_regime_labels import label_from_regime_dict, user_regime_label
from trendalgo.analytics.market_risk import atr_last, compute_risk
from trendalgo.analytics.market_structure import (
    EXTENSION_BARS,
    StructureExtras,
    confluence_count,
    corr_vs_btc,
    extension_stats,
    fib_levels_from_swing,
    has_real_volume,
    nearest_sr,
    session_vwap,
    spread_pct,
    volume_profile_lite,
)


@dataclass
class MarketContext:
    ok: bool = False
    error: str | None = None
    last_price: float | None = None
    regime_label: str | None = None
    consensus: dict[str, Any] | None = None
    pivots: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None
    structure: dict[str, Any] | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> MarketContext:
        if not isinstance(raw, dict):
            return cls(ok=False, error="missing")
        return cls(
            ok=bool(raw.get("ok")),
            error=str(raw["error"]) if raw.get("error") else None,
            last_price=_f(raw.get("last_price")),
            regime_label=str(raw["regime_label"]) if raw.get("regime_label") else None,
            consensus=raw.get("consensus") if isinstance(raw.get("consensus"), dict) else None,
            pivots=raw.get("pivots") if isinstance(raw.get("pivots"), dict) else None,
            risk=raw.get("risk") if isinstance(raw.get("risk"), dict) else None,
            structure=raw.get("structure") if isinstance(raw.get("structure"), dict) else None,
            extras=dict(raw.get("extras") or {}) if isinstance(raw.get("extras"), dict) else {},
        )

    @classmethod
    def empty(cls, error: str | None = None) -> MarketContext:
        return cls(ok=False, error=error)


def _f(raw: Any) -> float | None:
    try:
        if raw is None:
            return None
        return float(raw)
    except (TypeError, ValueError):
        return None


def _arrays(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float) if "high" in df.columns else closes
    lows = df["low"].to_numpy(dtype=float) if "low" in df.columns else closes
    vols = df["volume"].to_numpy(dtype=float) if "volume" in df.columns else None
    return highs, lows, closes, vols


def compute_market_context(
    df: pd.DataFrame | None,
    *,
    btc_closes: np.ndarray | None = None,
    bid: float | None = None,
    ask: float | None = None,
    period_bars: int = 24,
) -> MarketContext:
    """Build a pair snapshot; soft-fails to empty context on bad input."""
    if df is None or df.empty or "close" not in df.columns:
        return MarketContext.empty("no_candles")
    try:
        highs, lows, closes, vols = _arrays(df)
        if len(closes) < 10 or not np.isfinite(closes[-1]):
            return MarketContext.empty("short_history")

        last = float(closes[-1])
        pivots = compute_pivot_set(highs, lows, closes, period_bars=period_bars)
        consensus: ConsensusResult = compute_consensus(highs, lows, closes)

        regime_label = "Ranging"
        try:
            from trendalgo.backtest.secret_sauce_lab.regime_snapshot import detect_regime

            snap = detect_regime(df)
            regime_label = user_regime_label(
                structural=snap.structural,
                direction=snap.direction,
                volatility=snap.volatility,
                squeeze=snap.squeeze,
            )
        except Exception:
            regime_label = label_from_regime_dict(None)

        atr = atr_last(highs, lows, closes)
        price_map = pivots.price_map() if pivots else {}
        risk = compute_risk(
            last,
            atr,
            r1=price_map.get("R1"),
            r2=price_map.get("R2"),
        )

        vol_ok = has_real_volume(vols)
        vwap = session_vwap(closes, vols) if vol_ok and vols is not None else None
        poc, vah, val = (
            volume_profile_lite(highs, lows, closes, vols)
            if vol_ok and vols is not None
            else (None, None, None)
        )
        dd, ru = extension_stats(closes, bars=EXTENSION_BARS)
        corr = corr_vs_btc(closes, btc_closes)
        spr = spread_pct(bid, ask, last)

        ema20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else None
        fibs = fib_levels_from_swing(highs, lows, closes)
        conf = confluence_count(last, price_map, fib_levels=fibs, ema=ema20)
        near_name, near_pct, near_atr = nearest_sr(last, price_map, atr)

        structure = StructureExtras(
            nearest_sr_name=near_name,
            nearest_sr_pct=near_pct,
            nearest_sr_atr=near_atr,
            confluence=conf,
            vwap=round(vwap, 8) if vwap is not None else None,
            vwap_dist_pct=(round(100.0 * (last - vwap) / vwap, 3) if vwap and vwap > 0 else None),
            poc=round(poc, 8) if poc is not None else None,
            vah=round(vah, 8) if vah is not None else None,
            val=round(val, 8) if val is not None else None,
            drawdown_from_high_pct=dd,
            runup_from_low_pct=ru,
            btc_corr=corr,
            spread_pct=spr,
            volume_ok=vol_ok,
        )

        return MarketContext(
            ok=True,
            last_price=last,
            regime_label=regime_label,
            consensus=consensus.to_dict(),
            pivots=pivots.to_dict() if pivots else None,
            risk=risk.to_dict(),
            structure=structure.to_dict(),
            extras={"period_bars": period_bars, "extension_bars": EXTENSION_BARS},
        )
    except Exception as exc:  # soft-fail pane
        return MarketContext.empty(str(exc) or "compute_failed")
