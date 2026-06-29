"""Portfolio adapter protocol and shared helpers."""

from __future__ import annotations

from typing import Any, Protocol

from trendalgo.exchanges.asset_mapper import normalize_asset
from trendalgo.portfolio.db import HoldingRow, PortfolioStore


class PortfolioAdapter(Protocol):
    exchange_id: str

    def sync_balances(self, store: PortfolioStore, *, dry_run: bool = True) -> dict[str, Any]: ...


def holdings_from_ccxt_balance(
    balance: dict[str, Any],
    tickers: dict[str, Any],
    *,
    usd_aliases: frozenset[str] = frozenset({"USD", "ZUSD", "USDT"}),
) -> tuple[list[HoldingRow], float]:
    """Map CCXT balance + tickers to HoldingRow list and total USD."""
    holdings: list[HoldingRow] = []
    total_usd = 0.0
    for asset, qty in balance.get("total", {}).items():
        amount = float(qty or 0)
        if amount <= 0:
            continue
        normalized = normalize_asset(str(asset))
        if normalized in usd_aliases or normalized.startswith("USD"):
            price = 1.0
        else:
            pair = f"{normalized}/USD"
            ticker = tickers.get(pair) or tickers.get(f"{normalized}/USDT")
            price = float(ticker["last"]) if ticker and ticker.get("last") else 0.0
        value = amount * price
        cost = value * 0.92 if normalized not in usd_aliases else value
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
