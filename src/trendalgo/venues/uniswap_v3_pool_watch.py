"""Deterministic Uniswap V3 pool metrics for watch (dry-run default)."""

from __future__ import annotations

import hashlib
from typing import Any


def read_pool_state(
    rpc_url: str,
    pool_address: str,
    *,
    timeout_sec: float = 10.0,
) -> dict[str, Any]:
    """Optional live eth_call hook — v1 always falls back to dry hash metrics.

    ``rpc_url`` / ``timeout_sec`` reserved for a future slot0 reader; unused now
    so CI never depends on public RPC.
    """
    _ = (rpc_url, timeout_sec)
    return {"pool": pool_address.lower(), "mode": "stub"}


def estimate_metrics_from_state(
    state: dict[str, Any], pair: str
) -> tuple[float | None, float | None, float | None]:
    """Return (liquidity_usd, price_change_24h_pct, volume_proxy_usd)."""
    seed = hashlib.sha256(f"uni-v3-watch:{state.get('pool', '')}:{pair}".encode()).hexdigest()
    liq = round(50_000 + int(seed[:6], 16) % 450_000, 2)
    chg = round((int(seed[6:10], 16) % 2001 - 1000) / 100.0, 2)
    vol = round(10_000 + int(seed[10:16], 16) % 990_000, 2)
    return liq, chg, vol


def dry_run_metrics(pool_address: str, pair: str) -> tuple[float, float, float]:
    liq, chg, vol = estimate_metrics_from_state({"pool": pool_address.lower()}, pair)
    assert liq is not None and chg is not None and vol is not None
    return liq, chg, vol
