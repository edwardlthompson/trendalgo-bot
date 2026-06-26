"""Registry-driven wallet sync orchestration (S21–S22)."""

from __future__ import annotations

import os
from typing import Any

from trendalgo.portfolio.db import HoldingRow, PortfolioStore
from trendalgo.venues.registry import (
    get_lp_plugin,
    get_venue,
    get_wallet_plugin,
    load_venue_registry,
)


def _rpc_configured(rpc_env: str) -> bool:
    return bool(os.environ.get(rpc_env, "").strip())


def _read_lp_positions(address: str, *, venue_id: str, dry_run: bool) -> list[dict[str, Any]]:
    entry = get_venue(venue_id)
    positions: list[dict[str, Any]] = []
    for protocol in entry.portfolio_plugins:
        if protocol != "uniswap_v3":
            continue
        plugin = get_lp_plugin(venue_id, protocol)
        for row in plugin.read_lp_positions(address, dry_run=dry_run):
            positions.append({**row.to_dict(), "venue": venue_id})
    return positions


def preview_wallet(address: str, *, venue_id: str, include_lp: bool = True) -> dict[str, Any]:
    plugin = get_wallet_plugin(venue_id)
    addr = plugin.validate_address(address)
    holdings = plugin.read_balances(addr, dry_run=True)
    entry = get_venue(venue_id)
    lp_positions = _read_lp_positions(addr, venue_id=venue_id, dry_run=True) if include_lp else []
    lp_total = sum(float(p["liquidity_usd"]) for p in lp_positions)
    wallet_total = sum(h.value_usd for h in holdings)
    return {
        "venue": venue_id,
        "chain": venue_id,
        "chain_type": entry.chain_type,
        "address": addr,
        "total_usd": round(wallet_total + lp_total, 2),
        "wallet_total_usd": round(wallet_total, 2),
        "lp_total_usd": round(lp_total, 2),
        "holdings": [
            {"asset": h.asset, "quantity": h.quantity, "value_usd": h.value_usd} for h in holdings
        ],
        "lp_positions": lp_positions,
        "read_only": True,
        "rpc_configured": _rpc_configured(entry.rpc_env),
    }


def sync_wallet(
    store: PortfolioStore,
    address: str,
    *,
    venue_id: str,
    dry_run: bool = True,
    include_lp: bool = True,
) -> dict[str, Any]:
    plugin = get_wallet_plugin(venue_id)
    addr = plugin.validate_address(address)
    entry = get_venue(venue_id)
    use_live = (
        not dry_run
        and os.environ.get("ONCHAIN_SYNC_ENABLED") == "1"
        and _rpc_configured(entry.rpc_env)
    )
    holdings: list[HoldingRow] = plugin.read_balances(addr, dry_run=not use_live)
    lp_positions = (
        _read_lp_positions(addr, venue_id=venue_id, dry_run=not use_live) if include_lp else []
    )
    lp_total = sum(float(p["liquidity_usd"]) for p in lp_positions)
    source = f"{venue_id}_rpc" if use_live else f"{venue_id}_dry_run"

    account_id = store.get_or_create_account("onchain", f"{venue_id}:{addr}")
    store.set_account_meta(account_id, venue_id)
    wallet_total = sum(h.value_usd for h in holdings)
    total = wallet_total + lp_total
    store.insert_snapshot(account_id, total, holdings, source=source)

    return {
        "account_id": account_id,
        "venue": venue_id,
        "chain": venue_id,
        "chain_type": entry.chain_type,
        "address": addr,
        "source": source,
        "dry_run": not use_live,
        "total_usd": round(total, 2),
        "wallet_total_usd": round(wallet_total, 2),
        "lp_total_usd": round(lp_total, 2),
        "holdings": [
            {"asset": h.asset, "quantity": h.quantity, "value_usd": h.value_usd} for h in holdings
        ],
        "lp_positions": lp_positions,
        "read_only": True,
        "indexer": "none",
        "registry_version": load_venue_registry().version,
        "rpc_configured": _rpc_configured(entry.rpc_env),
    }
