"""Forex research/BT helpers (Alpaca rates; never live FX orders)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from trendalgo.brokers.forex_universe import is_forex_pair, normalize_fx_pair
from trendalgo.market.alpaca_forex import AlpacaForexRatesProvider
from trendalgo.market.fx_sessions import bar_unix_to_et_date, validate_fx_daily_bars

FX_BT_DISCLAIMER_SYNTHETIC = (
    "Forex research candles are synthetic/offline unless Alpaca forex rates are wired. "
    "Alpaca does not support FX trading."
)
FX_BT_DISCLAIMER_LIVE = (
    "Forex research candles from Alpaca forex rates. Alpaca does not support FX trading."
)


@dataclass(frozen=True)
class ForexBtResult:
    pair: str
    bar_count: int
    buy_hold_pct: float | None
    disclaimer: str
    source: str = "synthetic"
    gap_note: str = "ok"


def forex_buy_hold_bt(
    pair: str,
    *,
    lookback_days: int = 14,
    provider: AlpacaForexRatesProvider | None = None,
) -> ForexBtResult:
    fx = normalize_fx_pair(pair)
    if not is_forex_pair(fx):
        raise ValueError(f"pair not in Forex universe: {fx}")
    until = datetime.now(UTC)
    since = until - timedelta(days=max(1, lookback_days))
    eng = provider or AlpacaForexRatesProvider()
    points = eng.fetch("alpaca", fx, "1d", since, until)
    source = eng.last_source
    disclaimer = FX_BT_DISCLAIMER_LIVE if source == "alpaca" else FX_BT_DISCLAIMER_SYNTHETIC
    gaps = validate_fx_daily_bars(
        [bar_unix_to_et_date(p.time) for p in points],
        since=since.date(),
        until=until.date(),
    )
    bh: float | None = None
    if len(points) >= 2 and points[0].close > 0:
        bh = round((points[-1].close / points[0].close - 1.0) * 100.0, 4)
    return ForexBtResult(
        pair=fx,
        bar_count=len(points),
        buy_hold_pct=bh,
        disclaimer=disclaimer,
        source=source,
        gap_note=gaps.note,
    )
