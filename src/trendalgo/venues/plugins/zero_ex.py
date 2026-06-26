"""0x swap quote preview — read-only (S22)."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any

from trendalgo.venues.registry import get_venue

_CHAIN_IDS = {"ethereum": 1, "base": 8453, "arbitrum": 42161}
_ZERO_EX_HOST = "https://api.0x.org"


def _resolve_chain(chain: str) -> tuple[str, int]:
    venue_id = chain.strip().lower()
    entry = get_venue(venue_id)
    if entry.chain_type != "evm" or entry.chain_id is None:
        raise ValueError(f"0x quotes require EVM chain, got: {chain}")
    return venue_id, entry.chain_id


def _dry_quote(
    chain: str,
    sell_token: str,
    buy_token: str,
    sell_amount: float,
) -> dict[str, Any]:
    seed = hashlib.sha256(f"0x:{chain}:{sell_token}:{buy_token}:{sell_amount}".encode()).hexdigest()
    spread_bps = int(seed[:4], 16) % 50
    price = 1.0 + spread_bps / 10000
    buy_amount = round(sell_amount * price, 8)
    return {
        "chain": chain,
        "sell_token": sell_token.upper(),
        "buy_token": buy_token.upper(),
        "sell_amount": sell_amount,
        "buy_amount": buy_amount,
        "price": round(price, 8),
        "source": "dry-run",
        "read_only": True,
        "gas_estimate_usd": round(int(seed[4:8], 16) / 100, 2),
    }


def _live_quote(
    chain_id: int,
    sell_token: str,
    buy_token: str,
    sell_amount: float,
) -> dict[str, Any] | None:
    api_key = os.environ.get("ZERO_EX_API_KEY", "").strip()
    if not api_key:
        return None
    params = (
        f"chainId={chain_id}&sellToken={sell_token}&buyToken={buy_token}"
        f"&sellAmount={int(sell_amount * 1e18)}"
    )
    req = urllib.request.Request(
        f"{_ZERO_EX_HOST}/swap/permit2/price?{params}",
        headers={"0x-api-key": api_key, "0x-version": "v2"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
    buy_raw = body.get("buyAmount")
    if buy_raw is None:
        return None
    buy_amount = int(buy_raw) / 1e18
    return {
        "sell_token": sell_token.upper(),
        "buy_token": buy_token.upper(),
        "sell_amount": sell_amount,
        "buy_amount": round(buy_amount, 8),
        "price": round(buy_amount / sell_amount, 8) if sell_amount else 0.0,
        "source": "0x-api",
        "read_only": True,
        "gas_estimate_usd": None,
    }


def preview_quote(
    chain: str,
    sell_token: str,
    buy_token: str,
    sell_amount: float,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    if sell_amount <= 0:
        raise ValueError("sell_amount must be positive")
    venue_id, chain_id = _resolve_chain(chain)
    if not dry_run and os.environ.get("ZERO_EX_QUOTES_ENABLED") == "1":
        live = _live_quote(chain_id, sell_token, buy_token, sell_amount)
        if live is not None:
            return {**live, "chain": venue_id}
    return _dry_quote(venue_id, sell_token, buy_token, sell_amount)
