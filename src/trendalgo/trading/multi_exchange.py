"""Multi-exchange unified trading router (T27) — dry-run default, registry-aware (S13+)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from trendalgo.exchanges.pair_normalizer import normalize_pair
from trendalgo.exchanges.registry import get_entry, list_trading_exchanges
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.runner.adapters.registry import get_trading_adapter


def list_supported_exchanges() -> list[str]:
    return [e.id for e in list_trading_exchanges()]


def _host_exchange_control() -> ExchangeControlStore:
    """The host's own approval state, the same store the API routes use."""
    return ExchangeControlStore(
        Path(os.environ.get("TRENDALGO_DATA_DIR", "data")) / "exchange_control.db"
    )


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

    # H2: the one live gate. A dry run needs no approval. A live order is refused unless the
    # host's own approval state allows it, even when the caller passes no control store.
    gate = control if control is not None else (None if dry_run else _host_exchange_control())
    if gate is not None:
        ok, reason = gate.can_execute(exchange, dry_run=dry_run)
        if not ok:
            raise ValueError(reason)

    entry = get_entry(exchange)
    normalized_pair = normalize_pair(pair, exchange)
    adapter = get_trading_adapter(exchange)
    if not dry_run:
        # E1: size from a real ticker price. A failed fetch raises here, so no order is sent.
        price = adapter.reference_price(normalized_pair)
        result = adapter.submit_order(normalized_pair, side, amount, price)
        sizing = "priced"
    else:
        # Dry run never calls the exchange, so its base size is not a real price (E1).
        result = adapter.simulate_order(normalized_pair, side, amount, 1.0)
        sizing = "unpriced_dry_run"
    return {
        **result,
        "pair": normalized_pair,
        "unified_router": True,
        "status": result.get("status", "simulated"),
        "us_restricted": entry.us_restricted,
        "sizing": sizing,
    }
