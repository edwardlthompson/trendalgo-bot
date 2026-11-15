"""Solana JSON-RPC helpers (native SOL + SPL token accounts)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

# Common mainnet mints → display symbol (extend as needed).
_KNOWN_MINTS: dict[str, str] = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
}


def rpc_call(rpc_url: str, method: str, params: list[Any]) -> Any | None:
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
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
    if body.get("error"):
        return None
    return body.get("result")


def sol_balance(rpc_url: str, address: str) -> float | None:
    value = rpc_call(rpc_url, "getBalance", [address])
    if not isinstance(value, dict):
        return None
    lamports = value.get("value")
    if not isinstance(lamports, int):
        return None
    return lamports / 1e9


def spl_token_balances(rpc_url: str, address: str) -> list[tuple[str, float]]:
    """Return (symbol_or_mint, ui_amount) for non-zero SPL token accounts."""
    result = rpc_call(
        rpc_url,
        "getTokenAccountsByOwner",
        [
            address,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"},
        ],
    )
    if not isinstance(result, dict):
        return []
    out: list[tuple[str, float]] = []
    for row in result.get("value") or []:
        if not isinstance(row, dict):
            continue
        info = (((row.get("account") or {}).get("data") or {}).get("parsed") or {}).get(
            "info"
        ) or {}
        mint = str(info.get("mint") or "")
        tok = info.get("tokenAmount") or {}
        try:
            amount = float(tok.get("uiAmount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount <= 0 or not mint:
            continue
        symbol = _KNOWN_MINTS.get(mint, mint[:6])
        out.append((symbol, amount))
    return out
