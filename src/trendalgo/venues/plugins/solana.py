"""Solana wallet read plugin — native SOL + known SPL tokens."""

from __future__ import annotations

import hashlib
import os
import re

from trendalgo.portfolio.db import HoldingRow
from trendalgo.venues.base import VenueEntry
from trendalgo.venues.plugins.solana_rpc import sol_balance, spl_token_balances

_SOL_ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
_USD_STABLE = frozenset({"USDC", "USDT"})


class SolanaWalletReadPlugin:
    venue_id: str

    def __init__(self, entry: VenueEntry) -> None:
        self.entry = entry
        self.venue_id = entry.id

    def validate_address(self, address: str) -> str:
        addr = address.strip()
        if not _SOL_ADDRESS_RE.match(addr):
            raise ValueError("invalid Solana address")
        return addr

    def _dry_holdings(self, address: str) -> list[HoldingRow]:
        seed = hashlib.sha256(f"solana:{address}".encode()).hexdigest()
        sol_qty = int(seed[:4], 16) / 1000
        usdc_qty = int(seed[4:8], 16) / 10
        return [
            HoldingRow(
                asset="SOL",
                quantity=round(sol_qty, 4),
                price_usd=150.0,
                value_usd=round(sol_qty * 150.0, 2),
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

    def _live_holdings(self, address: str) -> list[HoldingRow] | None:
        rpc_url = os.environ.get(self.entry.rpc_env, "").strip()
        if not rpc_url:
            return None
        sol_qty = sol_balance(rpc_url, address)
        if sol_qty is None:
            return None
        rows = [
            HoldingRow(
                asset="SOL",
                quantity=round(sol_qty, 4),
                price_usd=150.0,
                value_usd=round(sol_qty * 150.0, 2),
                cost_basis_usd=0.0,
            )
        ]
        for symbol, amount in spl_token_balances(rpc_url, address):
            price = 1.0 if symbol in _USD_STABLE else 0.0
            rows.append(
                HoldingRow(
                    asset=symbol,
                    quantity=round(amount, 8),
                    price_usd=price,
                    value_usd=round(amount * price, 2),
                    cost_basis_usd=0.0,
                )
            )
        return rows

    def read_balances(self, address: str, *, dry_run: bool = True) -> list[HoldingRow]:
        addr = self.validate_address(address)
        live_ok = (
            not dry_run
            and os.environ.get("ONCHAIN_SYNC_ENABLED") == "1"
            and os.environ.get(self.entry.rpc_env, "").strip()
        )
        if live_ok:
            live = self._live_holdings(addr)
            if live is not None:
                return live
        return self._dry_holdings(addr)
