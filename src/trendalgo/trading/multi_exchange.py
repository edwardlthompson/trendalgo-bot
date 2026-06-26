"""Multi-exchange unified trading router (T27) — dry-run default, registry-aware (S13+)."""

from __future__ import annotations

import os
from typing import Any

from trendalgo.exchanges.pair_normalizer import normalize_pair
from trendalgo.exchanges.registry import get_entry, list_trading_exchanges
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.runner.adapters.registry import get_trading_adapter


def list_supported_exchanges() -> list[str]:
    return [e.id for e in list_trading_exchanges()]


def route_order(
    exchange: str,
    pair: str,
    side: str,
    amount: float,
    *,
    dry_run: bool = True,
    control: ExchangeControlStore | None = None,
) -> dict[str, Any]:
    """Route a spot order to an exchange adapter (simulated unless live keys + go-live)."""
    if exchange not in list_supported_exchanges():
        raise ValueError(f"unsupported exchange: {exchange}")
    if side not in ("buy", "sell"):
        raise ValueError("side must be buy or sell")
    if amount <= 0:
        raise ValueError("amount must be positive")

    if control is not None:
        ok, reason = control.can_execute(exchange, dry_run=dry_run)
        if not ok:
            raise ValueError(reason)

    entry = get_entry(exchange)
    normalized_pair = normalize_pair(pair, exchange)
    if not dry_run and entry.us_restricted and os.environ.get("WORLDWIDE_TRADING_ACK") != "1":
        raise ValueError("us_restricted exchange requires WORLDWIDE_TRADING_ACK=1 for live")

    adapter = get_trading_adapter(exchange)
    price = 1.0
    live_allowed = (
        not dry_run
        and os.environ.get("GO_LIVE_APPROVED") == "1"
        and entry.has_api_keys()
        and (control is None or bool((control.get(exchange) or {}).get("go_live_approved")))
    )
    if live_allowed:
        result = adapter.submit_order(normalized_pair, side, amount, price)
    else:
        result = adapter.simulate_order(normalized_pair, side, amount, price)
    return {
        **result,
        "pair": normalized_pair,
        "unified_router": True,
        "status": result.get("status", "simulated"),
        "us_restricted": entry.us_restricted,
    }
