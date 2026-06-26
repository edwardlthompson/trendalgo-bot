"""Solana wallet read plugin (S21)."""

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

_SOL_ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


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

    def _rpc_lamports(self, address: str) -> float | None:
        rpc_url = os.environ.get(self.entry.rpc_env, "").strip()
        if not rpc_url:
            return None
        payload = {
            "jsonrpc": "2.0",
            "method": "getBalance",
            "params": [address],
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
        value = body.get("result", {}).get("value")
        if not isinstance(value, int):
            return None
        return value / 1e9

    def read_balances(self, address: str, *, dry_run: bool = True) -> list[HoldingRow]:
        addr = self.validate_address(address)
        live_ok = (
            not dry_run
            and os.environ.get("ONCHAIN_SYNC_ENABLED") == "1"
            and os.environ.get(self.entry.rpc_env, "").strip()
        )
        if live_ok:
            sol_qty = self._rpc_lamports(addr)
            if sol_qty is not None:
                return [
                    HoldingRow(
                        asset="SOL",
                        quantity=round(sol_qty, 4),
                        price_usd=150.0,
                        value_usd=round(sol_qty * 150.0, 2),
                        cost_basis_usd=0.0,
                    )
                ]
        return self._dry_holdings(addr)
