"""Exchange fee fetchers — website (default) and CCXT (future API path)."""

from __future__ import annotations

from typing import Any

from trendalgo.exchanges.fee_website import FetchedFees, fetch_website_fees

__all__ = ["FetchedFees", "fetch_exchange_fees", "fetch_ccxt_fees", "retail_fees_from_trading"]


def fetch_exchange_fees(exchange_id: str, seed: dict[str, Any]) -> FetchedFees:
    """Primary path: public fee documentation pages (no trading API keys)."""
    return fetch_website_fees(exchange_id, seed)


def retail_fees_from_trading(trading: dict[str, Any]) -> tuple[float, float]:
    """CCXT helper — reserved for a future authenticated API fee sync."""
    tiers = trading.get("tiers") or {}
    taker_rows = tiers.get("taker")
    maker_rows = tiers.get("maker")
    taker = float(taker_rows[0][1]) if taker_rows else trading.get("taker")
    maker = float(maker_rows[0][1]) if maker_rows else trading.get("maker")
    if taker is None or maker is None:
        raise ValueError("missing taker/maker in CCXT trading fees")
    return float(taker), float(maker)


def fetch_ccxt_fees(ccxt_id: str) -> FetchedFees:
    """Optional future path — CCXT metadata (not used for paper-test fee sync)."""
    import ccxt

    exchange_class = getattr(ccxt, ccxt_id, None)
    if exchange_class is None:
        raise ValueError(f"ccxt has no exchange class: {ccxt_id}")
    exchange = exchange_class({"enableRateLimit": True})
    trading = (getattr(exchange, "fees", None) or {}).get("trading") or {}
    if not trading:
        raise ValueError(f"no CCXT trading fees for {ccxt_id}")
    taker, maker = retail_fees_from_trading(trading)
    return FetchedFees(
        taker_pct=taker,
        maker_pct=maker,
        source="ccxt",
        source_url="",
        verified=False,
    )
