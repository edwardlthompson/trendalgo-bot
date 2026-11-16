"""Alpaca scan → BT → paper stubs — paper-first; keyed OHLCV when available."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.brokers.tradfi_universe import is_tradfi_symbol, load_tradfi_universe
from trendalgo.market.alpaca_ohlcv import AlpacaOhlcvProvider, alpaca_credentials
from trendalgo.market.ohlcv_disk_cache import load_cached_ohlcv, save_cached_ohlcv
from trendalgo.market.us_equity_sessions import bar_unix_to_et_date, validate_daily_bars

ALPACA_BT_DISCLAIMER_SYNTHETIC = (
    "TradFi research candles are synthetic/offline unless a live market data feed is wired. "
    "Paper orders never hit a live brokerage account."
)
ALPACA_BT_DISCLAIMER_LIVE = (
    "TradFi research candles from Alpaca market data (IEX feed when available). "
    "Paper orders never hit a live brokerage account."
)


@dataclass(frozen=True)
class AlpacaScanHit:
    symbol: str
    venue: str
    note: str


@dataclass(frozen=True)
class AlpacaBtResult:
    symbol: str
    bar_count: int
    buy_hold_pct: float | None
    disclaimer: str
    source: str = "synthetic"
    gap_note: str = "ok"
    unexpected_gaps: int = 0


@dataclass(frozen=True)
class AlpacaPaperOrder:
    symbol: str
    side: str
    qty: float
    mode: str
    status: str
    order_id: str


def alpaca_scan_universe() -> tuple[AlpacaScanHit, ...]:
    """Public scan list for Alpaca paper research (universe file)."""
    return tuple(
        AlpacaScanHit(
            symbol=sym,
            venue="alpaca",
            note="TradFi universe — not Kraken Opportunity desk.",
        )
        for sym in load_tradfi_universe()
    )


def alpaca_buy_hold_bt(
    symbol: str,
    *,
    lookback_days: int = 14,
    provider: AlpacaOhlcvProvider | None = None,
    cache_root: Path | None = None,
) -> AlpacaBtResult:
    """Buy-and-hold BT: Alpaca bars when keyed, else labeled synthetic."""
    sym = symbol.strip().upper().split("/", 1)[0]
    if not is_tradfi_symbol(sym):
        # Allow BT for symbols in universe only (top-500 gate).
        raise ValueError(f"symbol not in TradFi universe: {sym}")
    until = datetime.now(UTC)
    since = until - timedelta(days=max(1, lookback_days))
    source = "synthetic"
    points = None
    if cache_root is not None:
        points = load_cached_ohlcv(cache_root, sym, "1d", since, until)
        if points is not None:
            source = "cache"
    if points is None:
        eng = provider or AlpacaOhlcvProvider()
        points = eng.fetch("alpaca", sym, "1d", since, until)
        source = eng.last_source
        if cache_root is not None and points:
            save_cached_ohlcv(cache_root, sym, "1d", since, until, points)
    disclaimer = (
        ALPACA_BT_DISCLAIMER_LIVE
        if source in {"alpaca", "cache"}
        else ALPACA_BT_DISCLAIMER_SYNTHETIC
    )
    bar_dates = [bar_unix_to_et_date(p.time) for p in points]
    gaps = validate_daily_bars(bar_dates, since=since.date(), until=until.date())
    bh: float | None = None
    if len(points) >= 2 and points[0].close > 0:
        bh = round((points[-1].close / points[0].close - 1.0) * 100.0, 4)
    return AlpacaBtResult(
        symbol=sym,
        bar_count=len(points),
        buy_hold_pct=bh,
        disclaimer=disclaimer,
        source=source,
        gap_note=gaps.note,
        unexpected_gaps=gaps.unexpected_gaps,
    )


def alpaca_paper_order(symbol: str, side: str, qty: float) -> AlpacaPaperOrder:
    """Simulated paper order (never live)."""
    sym = symbol.strip().upper()
    if side not in {"buy", "sell"}:
        raise ValueError("side must be buy or sell")
    if qty <= 0:
        raise ValueError("qty must be positive")
    return AlpacaPaperOrder(
        symbol=sym,
        side=side,
        qty=qty,
        mode="paper_dry_run",
        status="simulated",
        order_id=f"paper-alpaca-{sym.lower()}-{int(datetime.now(UTC).timestamp())}",
    )


def alpaca_research_bundle(symbol: str = "AAPL") -> dict[str, Any]:
    """One-shot research smoke for gates."""
    hits = alpaca_scan_universe()
    bt = alpaca_buy_hold_bt(symbol)
    order = alpaca_paper_order(symbol, "buy", 1.0)
    return {
        "scan_count": len(hits),
        "symbols": [h.symbol for h in hits],
        "in_universe": is_tradfi_symbol(symbol),
        "keyed": alpaca_credentials() is not None,
        "bt": {
            "symbol": bt.symbol,
            "bar_count": bt.bar_count,
            "buy_hold_pct": bt.buy_hold_pct,
            "disclaimer": bt.disclaimer,
            "source": bt.source,
            "gap_note": bt.gap_note,
            "unexpected_gaps": bt.unexpected_gaps,
        },
        "paper": {
            "symbol": order.symbol,
            "side": order.side,
            "qty": order.qty,
            "mode": order.mode,
            "status": order.status,
            "order_id": order.order_id,
        },
    }
