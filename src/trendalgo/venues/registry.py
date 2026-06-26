"""Venue registry — loads config/venues.registry.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from trendalgo.venues.base import LpReadPlugin, VenueEntry, WalletReadPlugin

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_REGISTRY = _REPO_ROOT / "config" / "venues.registry.json"


def _registry_path(path: Path | None = None) -> Path:
    if path is not None:
        return path
    env = os.environ.get("TRENDALGO_VENUE_REGISTRY")
    if env:
        return Path(env)
    for candidate in (_DEFAULT_REGISTRY, Path.cwd() / "config" / "venues.registry.json"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"venue registry not found (tried {_DEFAULT_REGISTRY})")


def _parse_entry(raw: dict[str, Any]) -> VenueEntry:
    chain_id = raw.get("chain_id")
    plugins = raw.get("portfolio_plugins") or []
    swap_plugins = raw.get("swap_plugins") or []
    sync_sec = raw.get("sync_interval_sec")
    return VenueEntry(
        id=str(raw["id"]),
        brand=str(raw["brand"]),
        chain_type=str(raw.get("chain_type", "evm")),
        native_symbol=str(raw.get("native_symbol", "ETH")),
        wallet_read_enabled=bool(raw.get("wallet_read_enabled", False)),
        trading_enabled=bool(raw.get("trading_enabled", False)),
        rpc_env=str(raw.get("rpc_env", "")),
        chain_id=int(chain_id) if chain_id is not None else None,
        portfolio_plugins=tuple(str(p) for p in plugins),
        swap_plugins=tuple(str(p) for p in swap_plugins),
        sync_interval_sec=int(sync_sec) if sync_sec is not None else None,
    )


@dataclass(frozen=True)
class VenueRegistry:
    version: int
    venues: tuple[VenueEntry, ...]
    default_sync_interval_sec: int = 2
    dex_live_phase: int = 0

    def by_id(self, venue_id: str) -> VenueEntry | None:
        for entry in self.venues:
            if entry.id == venue_id:
                return entry
        return None


@lru_cache(maxsize=1)
def load_venue_registry(path: Path | None = None) -> VenueRegistry:
    registry_path = _registry_path(path)
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    entries = tuple(_parse_entry(item) for item in data.get("venues", []))
    return VenueRegistry(
        version=int(data.get("version", 1)),
        venues=entries,
        default_sync_interval_sec=int(data.get("default_sync_interval_sec", 2)),
        dex_live_phase=int(data.get("dex_live_phase", 0)),
    )


def list_wallet_venues() -> list[VenueEntry]:
    return [v for v in load_venue_registry().venues if v.wallet_read_enabled]


def list_evm_wallet_venues() -> list[VenueEntry]:
    return [v for v in list_wallet_venues() if v.chain_type == "evm"]


def list_swap_venues() -> list[VenueEntry]:
    return [v for v in load_venue_registry().venues if v.swap_plugins]


def get_venue(venue_id: str) -> VenueEntry:
    entry = load_venue_registry().by_id(venue_id)
    if entry is None:
        raise KeyError(f"unknown venue: {venue_id}")
    return entry


def venue_public_dict(entry: VenueEntry) -> dict[str, Any]:
    data = entry.to_public_dict()
    data["rpc_configured"] = bool(entry.rpc_env and os.environ.get(entry.rpc_env, "").strip())
    return data


def get_wallet_plugin(venue_id: str) -> WalletReadPlugin:
    from trendalgo.venues.plugins.evm import EvmWalletReadPlugin
    from trendalgo.venues.plugins.solana import SolanaWalletReadPlugin

    entry = get_venue(venue_id)
    if not entry.wallet_read_enabled:
        raise KeyError(f"venue not enabled for wallet read: {venue_id}")
    if entry.chain_type == "solana":
        return SolanaWalletReadPlugin(entry)
    if entry.chain_type == "evm":
        return EvmWalletReadPlugin(entry)
    raise KeyError(f"unsupported chain_type: {entry.chain_type}")


def get_lp_plugin(venue_id: str, protocol: str = "uniswap_v3") -> LpReadPlugin:
    from trendalgo.venues.plugins.uniswap_v3 import UniswapV3LpPlugin

    entry = get_venue(venue_id)
    if protocol not in entry.portfolio_plugins:
        raise KeyError(f"protocol {protocol} not enabled for venue: {venue_id}")
    if protocol == "uniswap_v3":
        return UniswapV3LpPlugin(entry)
    raise KeyError(f"unsupported portfolio plugin: {protocol}")


def get_swap_plugin(venue_id: str, protocol: str | None = None):
    from trendalgo.dex.plugins.jupiter import JupiterSwapPlugin
    from trendalgo.dex.plugins.uniswap_v3_swap import UniswapV3SwapPlugin

    entry = get_venue(venue_id)
    if not entry.swap_plugins:
        raise KeyError(f"venue not enabled for swap: {venue_id}")
    chosen = protocol or entry.swap_plugins[0]
    if chosen not in entry.swap_plugins:
        raise KeyError(f"protocol {chosen} not enabled for venue: {venue_id}")
    if chosen == "uniswap_v3":
        return UniswapV3SwapPlugin(entry)
    if chosen == "jupiter":
        return JupiterSwapPlugin(entry)
    raise KeyError(f"unsupported swap plugin: {chosen}")
