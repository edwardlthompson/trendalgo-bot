"""Portfolio adapter protocol and shared helpers."""

from __future__ import annotations

from typing import Any, Protocol

from trendalgo.exchanges.asset_mapper import normalize_asset
from trendalgo.portfolio.db import HoldingRow, PortfolioStore


class PortfolioAdapter(Protocol):
    exchange_id: str

    def sync_balances(self, store: PortfolioStore, *, dry_run: bool = True) -> dict[str, Any]: ...


def _resolve_ticker(
    tickers: dict[str, Any],
    normalized: str,
    quote: str,
) -> dict[str, Any] | None:
    for candidate_quote in (quote, "USD", "USDT", "USDC"):
        ticker = tickers.get(f"{normalized}/{candidate_quote}")
        if isinstance(ticker, dict) and ticker.get("last") is not None:
            return ticker
    return None


def holdings_from_ccxt_balance(
    balance: dict[str, Any],
    tickers: dict[str, Any],
    *,
    usd_aliases: frozenset[str] = frozenset({"USD", "ZUSD", "USDT"}),
    quote_currency: str = "USD",
    prior_cost_basis: dict[str, tuple[float, float]] | None = None,
    honest_cost_basis: bool = False,
) -> tuple[list[HoldingRow], float]:
    """Map CCXT balance + tickers to HoldingRow list and total USD.

    Merges duplicate normalized symbols (e.g. ``SOL`` + ``SOL.S``). When
    ``honest_cost_basis=True``, preserves prior snapshot cost basis or uses
    current mark-to-market value (``$0`` unrealized on initial import) instead
    of fabricating an artificial discount.
    """
    quote = quote_currency.strip().upper() or "USD"
    all_usd = frozenset({*usd_aliases, "USD", "ZUSD", "USDT", "USDC"})
    merged_qty: dict[str, float] = {}
    for asset, qty in (balance.get("total") or {}).items():
        try:
            amount = float(qty or 0)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        normalized = normalize_asset(str(asset))
        merged_qty[normalized] = merged_qty.get(normalized, 0.0) + amount

    holdings: list[HoldingRow] = []
    total_usd = 0.0
    for normalized, amount in merged_qty.items():
        if normalized in all_usd or normalized.startswith("USD"):
            price = 1.0
        else:
            ticker = _resolve_ticker(tickers, normalized, quote)
            price = float(ticker["last"]) if ticker and ticker.get("last") else 0.0
        value = amount * price
        if normalized in all_usd:
            cost = value
        elif honest_cost_basis:
            prior = (prior_cost_basis or {}).get(normalized)
            if prior is not None and prior[0] > 0 and prior[1] > 0:
                prior_qty, prior_cost = prior
                if amount <= prior_qty:
                    cost = prior_cost * (amount / prior_qty)
                else:
                    cost = prior_cost + (amount - prior_qty) * price
            else:
                cost = value
        else:
            cost = value * 0.92
        holdings.append(
            HoldingRow(
                asset=normalized,
                quantity=amount,
                price_usd=price,
                value_usd=value,
                cost_basis_usd=cost,
            )
        )
        total_usd += value
    return holdings, total_usd
