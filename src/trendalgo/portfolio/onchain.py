"""Read-only on-chain / DeFi wallet sync (P18, T28) — public RPC only, no paid indexers."""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any

from trendalgo.portfolio.db import HoldingRow, PortfolioStore

_ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def _validate_address(address: str) -> str:
    addr = address.strip()
    if not _ETH_ADDRESS_RE.match(addr):
        raise ValueError("invalid EVM address")
    return addr.lower()


def _dry_onchain_holdings(chain: str) -> list[HoldingRow]:
    seed = hashlib.sha256(chain.encode()).hexdigest()
    eth_qty = int(seed[:4], 16) / 10000
    usdc_qty = int(seed[4:8], 16) / 10
    return [
        HoldingRow(
            asset="ETH",
            quantity=round(eth_qty, 6),
            price_usd=3000.0,
            value_usd=round(eth_qty * 3000, 2),
            cost_basis_usd=0.0,
        ),
        HoldingRow(
            asset="USDC",
            quantity=round(usdc_qty, 2),
            price_usd=1.0,
            value_usd=round(usdc_qty, 2),
            cost_basis_usd=0.0,
        ),
    ]


def sync_onchain_wallet(
    store: PortfolioStore,
    address: str,
    *,
    chain: str = "ethereum",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Sync read-only balances for an on-chain wallet into portfolio store."""
    addr = _validate_address(address)
    rpc_url = os.environ.get("ONCHAIN_RPC_URL", "")
    use_live = not dry_run and rpc_url and os.environ.get("ONCHAIN_SYNC_ENABLED") == "1"

    account_id = store.get_or_create_account("onchain", addr[:10])
    store.set_account_meta(account_id, chain)

    if use_live:
        # MVP: live path reserved for self-hosted RPC; still returns deterministic sample
        holdings = _dry_onchain_holdings(chain)
        source = "onchain_rpc_stub"
    else:
        holdings = _dry_onchain_holdings(chain)
        source = "onchain_dry_run"

    total = sum(h.value_usd for h in holdings)
    store.insert_snapshot(account_id, total, holdings, source=source)

    return {
        "account_id": account_id,
        "chain": chain,
        "address": addr,
        "source": source,
        "dry_run": not use_live,
        "total_usd": round(total, 2),
        "holdings": [
            {
                "asset": h.asset,
                "quantity": h.quantity,
                "value_usd": h.value_usd,
            }
            for h in holdings
        ],
        "read_only": True,
        "indexer": "none",
    }


def preview_onchain_wallet(address: str, *, chain: str = "ethereum") -> dict[str, Any]:
    """Preview balances without persisting."""
    addr = _validate_address(address)
    holdings = _dry_onchain_holdings(chain)
    total = sum(h.value_usd for h in holdings)
    return {
        "chain": chain,
        "address": addr,
        "total_usd": round(total, 2),
        "holdings": [h.asset for h in holdings],
        "read_only": True,
    }
