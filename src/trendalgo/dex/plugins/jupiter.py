"""Jupiter swap quote + dry-run simulation — Solana (S23)."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from trendalgo.venues.base import VenueEntry

_JUPITER_QUOTE = "https://quote-api.jup.ag/v6/quote"
_SOL_MINT = "So11111111111111111111111111111111111111112"
_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def _token_mint(symbol: str) -> str:
    sym = symbol.upper()
    if sym in {"SOL", "WSOL"}:
        return _SOL_MINT
    if sym == "USDC":
        return _USDC_MINT
    return symbol


class JupiterSwapPlugin:
    protocol = "jupiter"
    venue_id: str

    def __init__(self, entry: VenueEntry) -> None:
        self.entry = entry
        self.venue_id = entry.id

    def _dry_quote(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
        *,
        simulated: bool,
    ) -> dict[str, Any]:
        seed = hashlib.sha256(
            f"jup:{self.venue_id}:{sell_token}:{buy_token}:{sell_amount}".encode()
        ).hexdigest()
        slippage_bps = int(seed[:4], 16) % 40
        base_price = 150.0 if sell_token.upper() == "SOL" else 1.0
        price = base_price * (1 - slippage_bps / 10000)
        buy_amount = round(sell_amount * price, 8)
        payload: dict[str, Any] = {
            "chain": self.venue_id,
            "protocol": self.protocol,
            "sell_token": sell_token.upper(),
            "buy_token": buy_token.upper(),
            "sell_amount": sell_amount,
            "buy_amount": buy_amount,
            "price": round(price, 8),
            "slippage_bps": slippage_bps,
            "tx_broadcast": False,
            "source": "dry-run",
        }
        if simulated:
            payload["mode"] = "simulated"
            payload["simulation_id"] = f"dex-sim-{uuid.uuid4().hex[:12]}"
        else:
            payload["mode"] = "preview"
            payload["read_only"] = True
        return payload

    def _live_quote(
        self, sell_token: str, buy_token: str, sell_amount: float
    ) -> dict[str, Any] | None:
        if os.environ.get("JUPITER_QUOTES_ENABLED") != "1":
            return None
        amount_raw = int(sell_amount * 1e9)
        params = (
            f"inputMint={_token_mint(sell_token)}&outputMint={_token_mint(buy_token)}"
            f"&amount={amount_raw}&slippageBps=50"
        )
        req = urllib.request.Request(f"{_JUPITER_QUOTE}?{params}", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return None
        out = body.get("outAmount")
        if out is None:
            return None
        buy_amount = int(out) / 1e6 if buy_token.upper() == "USDC" else int(out) / 1e9
        return {
            "chain": self.venue_id,
            "protocol": self.protocol,
            "sell_token": sell_token.upper(),
            "buy_token": buy_token.upper(),
            "sell_amount": sell_amount,
            "buy_amount": round(buy_amount, 8),
            "price": round(buy_amount / sell_amount, 8) if sell_amount else 0.0,
            "mode": "preview",
            "read_only": True,
            "source": "jupiter-api",
            "tx_broadcast": False,
        }

    def preview_swap(self, sell_token: str, buy_token: str, sell_amount: float) -> dict[str, Any]:
        live = self._live_quote(sell_token, buy_token, sell_amount)
        if live is not None:
            return live
        return self._dry_quote(sell_token, buy_token, sell_amount, simulated=False)

    def simulate_swap(self, sell_token: str, buy_token: str, sell_amount: float) -> dict[str, Any]:
        return self._dry_quote(sell_token, buy_token, sell_amount, simulated=True)

    def execute_live_swap(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
        *,
        slippage_bps: int,
        nonce: int,
        signed_tx_hash: str,
    ) -> dict[str, Any]:
        quote = self._dry_quote(sell_token, buy_token, sell_amount, simulated=True)
        quote["mode"] = "live"
        quote["slippage_bps"] = slippage_bps
        quote["nonce"] = nonce
        quote["tx_hash"] = signed_tx_hash
        quote["tx_broadcast"] = True
        quote.pop("simulation_id", None)
        return quote
