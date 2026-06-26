"""DEX portfolio positions for API (S22)."""

from __future__ import annotations

from typing import Any

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.venues.registry import get_venue, list_evm_wallet_venues
from trendalgo.venues.wallet_sync import preview_wallet


def preview_dex_positions(
    address: str,
    *,
    chain: str | None = None,
) -> dict[str, Any]:
    if chain:
        return preview_wallet(address, venue_id=chain.strip().lower(), include_lp=True)
    positions: list[dict[str, Any]] = []
    total_lp = 0.0
    for entry in list_evm_wallet_venues():
        if not entry.portfolio_plugins:
            continue
        preview = preview_wallet(address, venue_id=entry.id, include_lp=True)
        for lp in preview.get("lp_positions", []):
            positions.append(lp)
            total_lp += float(lp.get("liquidity_usd", 0))
    return {
        "address": address,
        "chain": "all-evm",
        "lp_positions": positions,
        "lp_total_usd": round(total_lp, 2),
        "read_only": True,
    }


def list_dex_positions_from_store(store: PortfolioStore) -> dict[str, Any]:
    """Aggregate LP positions from synced onchain accounts."""
    accounts = [a for a in store.list_accounts() if a["exchange"] == "onchain"]
    all_positions: list[dict[str, Any]] = []
    total_lp = 0.0
    for acc in accounts:
        label = str(acc["label"])
        if ":" not in label:
            continue
        venue_id, address = label.split(":", 1)
        try:
            entry = get_venue(venue_id)
        except KeyError:
            continue
        if not entry.portfolio_plugins:
            continue
        preview = preview_wallet(address, venue_id=entry.id, include_lp=True)
        for lp in preview.get("lp_positions", []):
            item = {**lp, "account_id": int(acc["id"]), "address": address}
            all_positions.append(item)
            total_lp += float(lp.get("liquidity_usd", 0))
    return {
        "accounts": len(accounts),
        "lp_positions": all_positions,
        "lp_total_usd": round(total_lp, 2),
        "read_only": True,
    }
