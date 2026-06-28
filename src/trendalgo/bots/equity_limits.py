"""Bot equity caps from portfolio holdings."""

from __future__ import annotations

from typing import Any

from trendalgo.market.symbols import base_symbol, quote_symbol


def _holding_qty(holdings: list[dict[str, Any]], symbol: str) -> float:
    sym = symbol.upper()
    total = 0.0
    for row in holdings:
        if str(row.get("symbol", "")).upper() == sym:
            total += float(row.get("quantity", 0) or 0)
    return total


def bot_equity_limits(state: Any, pair: str, *, paper: bool = False) -> dict[str, Any]:
    base = base_symbol(pair)
    quote = quote_symbol(pair)
    if paper:
        return {
            "base": {"symbol": base, "max": 10.0},
            "quote": {"symbol": quote, "max": 50_000.0},
            "portfolio_usd": 100_000.0,
            "paper": True,
        }
    from trendalgo.portfolio.overview import build_portfolio_overview

    overview = build_portfolio_overview(state)
    holdings = list(overview.get("holdings") or [])
    return {
        "base": {"symbol": base, "max": _holding_qty(holdings, base)},
        "quote": {"symbol": quote, "max": _holding_qty(holdings, quote)},
        "portfolio_usd": float(overview.get("net_worth_usd", 0) or 0),
        "paper": False,
    }


def normalize_equity_mode(mode: str | None) -> str:
    raw = str(mode or "quote").lower()
    if raw in {"usd", "manual", "quote"}:
        return "quote"
    if raw in {"pct", "portfolio_pct", "portfolio"}:
        return "portfolio_pct"
    if raw == "base":
        return "base"
    return "quote"


def validate_equity_input(
    state: Any,
    pair: str,
    mode: str,
    equity_input: float,
    *,
    paper: bool = False,
) -> None:
    resolved = normalize_equity_mode(mode)
    if equity_input <= 0:
        raise ValueError("equity amount must be greater than zero")
    if resolved == "portfolio_pct":
        if equity_input > 100:
            raise ValueError("portfolio percentage cannot exceed 100")
        return
    limits = bot_equity_limits(state, pair, paper=paper)
    if resolved == "base":
        cap = float(limits["base"]["max"])
        if equity_input > cap:
            sym = limits["base"]["symbol"]
            raise ValueError(f"base amount exceeds available {sym} holdings ({cap})")
        return
    cap = float(limits["quote"]["max"])
    if equity_input > cap:
        sym = limits["quote"]["symbol"]
        raise ValueError(f"quote amount exceeds available {sym} holdings ({cap})")


def resolve_equity_usd(
    state: Any,
    pair: str,
    mode: str,
    equity_input: float,
    equity_usd_fallback: float,
    *,
    mark_price: float | None = None,
) -> float:
    resolved = normalize_equity_mode(mode)
    if resolved == "portfolio_pct":
        limits = bot_equity_limits(state, pair, paper=bool(state.bot.dry_run))
        net = float(limits.get("portfolio_usd") or equity_usd_fallback)
        pct = min(100.0, max(0.0, float(equity_input)))
        return max(1.0, net * (pct / 100.0))
    if resolved == "quote":
        quote = quote_symbol(pair)
        if quote in {"USD", "USDT", "USDC", "DAI"}:
            return max(1.0, float(equity_input))
        px = mark_price if mark_price and mark_price > 0 else 1.0
        return max(1.0, float(equity_input) * px)
    px = mark_price if mark_price and mark_price > 0 else 1.0
    return max(1.0, float(equity_input) * px)

