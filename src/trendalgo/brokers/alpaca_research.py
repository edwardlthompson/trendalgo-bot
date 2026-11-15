"""Alpaca scan → BT → paper stubs after TF-P1 (TF-P2…P4) — paper-first, offline-safe."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.market.synthetic import synthetic_ohlcv

# Curated liquid US equity majors for paper research (not a full desk).
_PAPER_UNIVERSE: tuple[str, ...] = ("AAPL", "MSFT", "SPY", "QQQ", "IWM")


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


@dataclass(frozen=True)
class AlpacaPaperOrder:
    symbol: str
    side: str
    qty: float
    mode: str
    status: str
    order_id: str


ALPACA_BT_DISCLAIMER = (
    "TradFi research candles are synthetic/offline unless a live market data feed is wired. "
    "Paper orders never hit a live brokerage account."
)


def alpaca_scan_universe() -> tuple[AlpacaScanHit, ...]:
    """TF-P2: thin public scan list for Alpaca paper research."""
    return tuple(
        AlpacaScanHit(
            symbol=sym,
            venue="alpaca",
            note="Paper universe — not Kraken Opportunity desk.",
        )
        for sym in _PAPER_UNIVERSE
    )


def alpaca_buy_hold_bt(symbol: str, *, lookback_days: int = 14) -> AlpacaBtResult:
    """TF-P3: synthetic buy-and-hold for a paper-universe symbol."""
    sym = symbol.strip().upper()
    until = datetime.now(UTC)
    since = until - timedelta(days=max(1, lookback_days))
    points = synthetic_ohlcv(f"{sym}/USD", "1d", since, until)
    bh: float | None = None
    if len(points) >= 2 and points[0].close > 0:
        bh = round((points[-1].close / points[0].close - 1.0) * 100.0, 4)
    return AlpacaBtResult(
        symbol=sym,
        bar_count=len(points),
        buy_hold_pct=bh,
        disclaimer=ALPACA_BT_DISCLAIMER,
    )


def alpaca_paper_order(symbol: str, side: str, qty: float) -> AlpacaPaperOrder:
    """TF-P4: simulated paper order (never live)."""
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
    """One-shot TF-P2…P4 smoke for gates."""
    hits = alpaca_scan_universe()
    bt = alpaca_buy_hold_bt(symbol)
    order = alpaca_paper_order(symbol, "buy", 1.0)
    return {
        "scan_count": len(hits),
        "symbols": [h.symbol for h in hits],
        "bt": {
            "symbol": bt.symbol,
            "bar_count": bt.bar_count,
            "buy_hold_pct": bt.buy_hold_pct,
            "disclaimer": bt.disclaimer,
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
