"""Uniswap V3 LP position read plugin — EVM chains (S22)."""

from __future__ import annotations

import hashlib
import re

from trendalgo.venues.base import LpPositionRow, VenueEntry

_ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


class UniswapV3LpPlugin:
    protocol = "uniswap_v3"
    venue_id: str

    def __init__(self, entry: VenueEntry) -> None:
        self.entry = entry
        self.venue_id = entry.id

    def validate_address(self, address: str) -> str:
        addr = address.strip()
        if not _ETH_ADDRESS_RE.match(addr):
            raise ValueError("invalid EVM address")
        return addr.lower()

    def _dry_positions(self, address: str) -> list[LpPositionRow]:
        seed = hashlib.sha256(f"uni-v3:{self.venue_id}:{address}".encode()).hexdigest()
        liq_a = round(int(seed[8:12], 16) / 2, 2)
        liq_b = round(int(seed[12:16], 16) / 4, 2)
        return [
            LpPositionRow(
                protocol=self.protocol,
                pool_id=f"0x{seed[:40]}",
                pair="ETH/USDC",
                liquidity_usd=liq_a,
                fee_tier=3000,
                in_range=True,
            ),
            LpPositionRow(
                protocol=self.protocol,
                pool_id=f"0x{seed[16:56]}",
                pair="ETH/USDT",
                liquidity_usd=liq_b,
                fee_tier=500,
                in_range=int(seed[56:58], 16) % 2 == 0,
            ),
        ]

    def read_lp_positions(self, address: str, *, dry_run: bool = True) -> list[LpPositionRow]:
        addr = self.validate_address(address)
        if dry_run or not self.entry.rpc_env:
            return self._dry_positions(addr)
        return self._dry_positions(addr)
