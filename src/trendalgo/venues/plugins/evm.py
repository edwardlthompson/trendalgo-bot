"""EVM wallet read plugin — ethereum, base, arbitrum (S21)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from trendalgo.portfolio.db import HoldingRow
from trendalgo.venues.base import VenueEntry

_ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


class EvmWalletReadPlugin:
    venue_id: str

    def __init__(self, entry: VenueEntry) -> None:
        self.entry = entry
        self.venue_id = entry.id

    def validate_address(self, address: str) -> str:
        addr = address.strip()
        if not _ETH_ADDRESS_RE.match(addr):
            raise ValueError("invalid EVM address")
        return addr.lower()

    def _dry_holdings(self, address: str) -> list[HoldingRow]:
        seed = hashlib.sha256(f"{self.venue_id}:{address}".encode()).hexdigest()
        native_qty = int(seed[:4], 16) / 10000
        stable_qty = int(seed[4:8], 16) / 10
        native = self.entry.native_symbol
        stable = "USDC"
        return [
            HoldingRow(
                asset=native,
                quantity=round(native_qty, 6),
                price_usd=3000.0 if native == "ETH" else 1.0,
                value_usd=round(native_qty * (3000.0 if native == "ETH" else 1.0), 2),
                cost_basis_usd=0.0,
            ),
            HoldingRow(
                asset=stable,
                quantity=round(stable_qty, 2),
                price_usd=1.0,
                value_usd=round(stable_qty, 2),
                cost_basis_usd=0.0,
            ),
        ]

    def _rpc_native_balance(self, address: str) -> float | None:
        rpc_url = os.environ.get(self.entry.rpc_env, "").strip()
        if not rpc_url:
            return None
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [address, "latest"],
            "id": 1,
        }
        req = urllib.request.Request(
            rpc_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return None
        result = body.get("result")
        if not isinstance(result, str):
            return None
        wei = int(result, 16)
        return wei / 1e18

    def read_balances(self, address: str, *, dry_run: bool = True) -> list[HoldingRow]:
        addr = self.validate_address(address)
        live_ok = (
            not dry_run
            and os.environ.get("ONCHAIN_SYNC_ENABLED") == "1"
            and os.environ.get(self.entry.rpc_env, "").strip()
        )
        if live_ok:
            native_qty = self._rpc_native_balance(addr)
            if native_qty is not None:
                native = self.entry.native_symbol
                price = 3000.0 if native == "ETH" else 1.0
                return [
                    HoldingRow(
                        asset=native,
                        quantity=round(native_qty, 6),
                        price_usd=price,
                        value_usd=round(native_qty * price, 2),
                        cost_basis_usd=0.0,
                    )
                ]
        return self._dry_holdings(addr)
