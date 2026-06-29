"""DEX swap router — registry-driven plugin dispatch (S23–S24)."""

from __future__ import annotations

from typing import Any

from trendalgo.dex.control import DexVenueControlStore
from trendalgo.dex.gates import validate_dex_swap_access
from trendalgo.dex.nonce import NonceStore
from trendalgo.dex.signer import signer_configured
from trendalgo.venues.registry import (
    get_swap_plugin,
    get_venue,
    list_swap_venues,
    load_venue_registry,
)


def list_dex_swap_chains() -> list[str]:
    return [v.id for v in list_swap_venues()]


def list_live_trading_venues() -> list[str]:
    return [v.id for v in list_swap_venues() if v.trading_enabled]


def _resolve_chain(chain: str) -> str:
    venue_id = chain.strip().lower()
    entry = get_venue(venue_id)
    if not entry.swap_plugins:
        raise ValueError(f"chain has no swap plugins: {chain}")
    return venue_id


def preview_dex_swap(
    chain: str,
    sell_token: str,
    buy_token: str,
    sell_amount: float,
) -> dict[str, Any]:
    if sell_amount <= 0:
        raise ValueError("sell_amount must be positive")
    venue_id = _resolve_chain(chain)
    plugin = get_swap_plugin(venue_id)
    result = plugin.preview_swap(sell_token, buy_token, sell_amount)
    return {**result, "registry_version": load_venue_registry().version}


def dry_run_dex_swap(
    chain: str,
    sell_token: str,
    buy_token: str,
    sell_amount: float,
    *,
    app_dry_run: bool = True,
    live_swap: bool = False,
) -> dict[str, Any]:
    if sell_amount <= 0:
        raise ValueError("sell_amount must be positive")
    validate_dex_swap_access(app_dry_run=app_dry_run, live_swap=live_swap)
    venue_id = _resolve_chain(chain)
    entry = get_venue(venue_id)
    plugin = get_swap_plugin(venue_id)
    result = plugin.simulate_swap(sell_token, buy_token, sell_amount)
    return {
        **result,
        "registry_version": load_venue_registry().version,
        "trading_enabled": entry.trading_enabled,
    }


def live_dex_swap(
    chain: str,
    sell_token: str,
    buy_token: str,
    sell_amount: float,
    *,
    control: DexVenueControlStore,
    nonce_store: NonceStore,
    slippage_bps: int = 50,
) -> dict[str, Any]:
    from trendalgo.dex.runner.live import LiveSwapRunner

    runner = LiveSwapRunner(control=control, nonce_store=nonce_store)
    return runner.execute(chain, sell_token, buy_token, sell_amount, slippage_bps=slippage_bps)


def dex_trading_status() -> dict[str, Any]:
    registry = load_venue_registry()
    venues = []
    for entry in list_swap_venues():
        venues.append(
            {
                "id": entry.id,
                "trading_enabled": entry.trading_enabled,
                "swap_plugins": list(entry.swap_plugins),
                "signer_configured": signer_configured(),
            }
        )
    return {
        "registry_version": registry.version,
        "dex_live_phase": registry.dex_live_phase,
        "venues": venues,
        "live_trading_venues": list_live_trading_venues(),
    }
