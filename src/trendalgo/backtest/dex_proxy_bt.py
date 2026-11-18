"""Optional CEX-proxy backtest for DEX majors — honest “not on-chain fills” (DEX-P3a)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.market.dex_candle_provider import Prefer, fetch_dex_candles

DEX_PROXY_BT_DISCLAIMER = (
    "Not on-chain fills — candles are a labeled CEX spot proxy or synthetic research series. "
    "Do not treat results as Uniswap execution prices."
)


@dataclass(frozen=True)
class DexProxyBtResult:
    venue_id: str
    pair: str
    candle_kind: str
    bar_count: int
    buy_hold_pct: float | None
    disclaimer: str
    degraded: bool


def run_dex_proxy_buy_hold(
    venue_id: str,
    pair: str,
    *,
    timeframe: str = "1h",
    lookback_days: int = 7,
    prefer: Prefer = "synthetic",
) -> DexProxyBtResult:
    """Smoke buy-and-hold on labeled DEX candles (research only)."""
    until = datetime.now(UTC)
    since = until - timedelta(days=max(1, lookback_days))
    candles = fetch_dex_candles(venue_id, pair, timeframe, since, until, prefer=prefer)
    pts = candles.points
    bh: float | None = None
    if len(pts) >= 2 and pts[0].close > 0:
        bh = round((pts[-1].close / pts[0].close - 1.0) * 100.0, 4)
    return DexProxyBtResult(
        venue_id=venue_id,
        pair=pair,
        candle_kind=candles.meta.kind,
        bar_count=len(pts),
        buy_hold_pct=bh,
        disclaimer=DEX_PROXY_BT_DISCLAIMER,
        degraded=bool(candles.meta.degraded),
    )


def dex_proxy_bt_public_dict(result: DexProxyBtResult) -> dict[str, Any]:
    return {
        "venue_id": result.venue_id,
        "pair": result.pair,
        "candle_kind": result.candle_kind,
        "bar_count": result.bar_count,
        "buy_hold_pct": result.buy_hold_pct,
        "disclaimer": result.disclaimer,
        "degraded": result.degraded,
        "on_chain_fills": False,
    }
