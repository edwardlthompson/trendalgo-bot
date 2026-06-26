"""Venue plugin contracts — wallet read (S21) + portfolio read (S22)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from trendalgo.portfolio.db import HoldingRow


@dataclass(frozen=True)
class VenueEntry:
    id: str
    brand: str
    chain_type: str
    native_symbol: str
    wallet_read_enabled: bool
    trading_enabled: bool
    rpc_env: str
    chain_id: int | None = None
    portfolio_plugins: tuple[str, ...] = ()
    swap_plugins: tuple[str, ...] = ()
    sync_interval_sec: int | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "brand": self.brand,
            "chain_type": self.chain_type,
            "chain_id": self.chain_id,
            "native_symbol": self.native_symbol,
            "wallet_read_enabled": self.wallet_read_enabled,
            "trading_enabled": self.trading_enabled,
            "portfolio_plugins": list(self.portfolio_plugins),
            "swap_plugins": list(self.swap_plugins),
            "rpc_configured": False,
        }


@dataclass(frozen=True)
class LpPositionRow:
    protocol: str
    pool_id: str
    pair: str
    liquidity_usd: float
    fee_tier: int
    in_range: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "pool_id": self.pool_id,
            "pair": self.pair,
            "liquidity_usd": self.liquidity_usd,
            "fee_tier": self.fee_tier,
            "in_range": self.in_range,
        }


class WalletReadPlugin(Protocol):
    venue_id: str

    def validate_address(self, address: str) -> str: ...

    def read_balances(self, address: str, *, dry_run: bool = True) -> list[HoldingRow]: ...


class LpReadPlugin(Protocol):
    protocol: str
    venue_id: str

    def read_lp_positions(self, address: str, *, dry_run: bool = True) -> list[LpPositionRow]: ...
