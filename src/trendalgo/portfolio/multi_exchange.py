"""Multi-exchange read-only aggregation (P12, P13) — registry-driven (S13)."""

from __future__ import annotations

from typing import Any

from trendalgo.exchanges.asset_mapper import normalize_asset
from trendalgo.exchanges.sync import sync_all_exchanges
from trendalgo.portfolio.db import PortfolioStore

__all__ = ["aggregate_holdings", "sync_all_exchanges"]


def aggregate_holdings(store: PortfolioStore) -> dict[str, Any]:
    accounts = store.list_accounts()
    merged: dict[str, dict[str, float]] = {}
    account_summaries: list[dict[str, Any]] = []
    total_usd = 0.0

    for acc in accounts:
        snap = store.latest_snapshot(int(acc["id"]))
        if not snap:
            continue
        acc_total = float(snap["total_usd"])
        total_usd += acc_total
        meta = store.get_account_meta(int(acc["id"]))
        account_summaries.append(
            {
                "account_id": int(acc["id"]),
                "exchange": acc["exchange"],
                "label": acc["label"],
                "account_type": meta.get("account_type", "spot"),
                "total_usd": acc_total,
                "holdings_count": len(snap.get("holdings", [])),
            }
        )
        for h in snap.get("holdings", []):
            asset = normalize_asset(str(h["asset"]))
            manual_cost = store.get_manual_cost_basis(int(acc["id"]), asset)
            cost = float(manual_cost if manual_cost is not None else h.get("cost_basis_usd", 0))
            qty = float(h["quantity"])
            value = float(h["value_usd"])
            price = float(h["price_usd"])
            if asset not in merged:
                merged[asset] = {
                    "quantity": 0.0,
                    "value_usd": 0.0,
                    "cost_basis_usd": 0.0,
                    "price_usd": price,
                }
            merged[asset]["quantity"] += qty
            merged[asset]["value_usd"] += value
            merged[asset]["cost_basis_usd"] += cost
            merged[asset]["price_usd"] = price

    holdings = [
        {
            "asset": asset,
            "quantity": round(vals["quantity"], 8),
            "price_usd": vals["price_usd"],
            "value_usd": round(vals["value_usd"], 2),
            "cost_basis_usd": round(vals["cost_basis_usd"], 2),
        }
        for asset, vals in merged.items()
    ]
    account_summaries.sort(key=lambda a: float(a["total_usd"]), reverse=True)
    return {
        "accounts": account_summaries,
        "holdings": sorted(holdings, key=lambda h: h["value_usd"], reverse=True),
        "total_usd": round(total_usd, 2),
        "exchange_count": len(account_summaries),
    }
