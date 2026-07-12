"""Opt-in bridge from audited TradingView signals to trading adapters."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Protocol

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.multi_exchange import route_order


class BridgeState(Protocol):
    portfolio_store: PortfolioStore
    exchange_control: ExchangeControlStore
    bot: Any

    def log(self, message: str) -> None: ...


def _execution_audit(
    store: PortfolioStore,
    signal: dict[str, Any],
    *,
    accepted: bool,
    reason: str,
) -> None:
    canonical = json.dumps(signal, sort_keys=True, separators=(",", ":")).encode()
    store.insert_webhook_audit(
        client_ip="internal",
        payload_hash=hashlib.sha256(canonical).hexdigest(),
        accepted=accepted,
        reason=reason,
        source="tradingview-execution",
    )


def bridge_tradingview_signal(signal: dict[str, Any], state: BridgeState) -> dict[str, Any]:
    """Map an accepted webhook signal to a paper/live order tick when acknowledged."""
    if os.environ.get("TV_EXECUTION_ACK") != "1":
        state.log(f"tradingview log-only: {signal}")
        return {"status": "log_only", "executed": False}

    aliases = {"buy": "buy", "long": "buy", "sell": "sell", "short": "sell"}
    action = aliases.get(str(signal.get("action", "")).lower())
    pair = str(signal.get("pair", "")).strip()
    exchange = str(signal.get("exchange_id") or os.environ.get("TV_EXECUTION_EXCHANGE", "kraken"))
    try:
        amount = float(signal.get("amount_usd") or os.environ.get("TV_EXECUTION_AMOUNT_USD", "25"))
        if not pair or action is None:
            raise ValueError("signal requires pair and buy/sell action")
        result = route_order(
            exchange,
            pair,
            action,
            amount,
            dry_run=bool(state.bot.dry_run),
            control=state.exchange_control,
        )
    except (TypeError, ValueError) as exc:
        reason = str(exc)
        _execution_audit(state.portfolio_store, signal, accepted=False, reason=reason)
        state.log(f"tradingview execution failed: {reason}")
        return {"status": "failed", "executed": False, "error": reason}

    tick = {
        "pair": result["pair"],
        "action": action,
        "exchange_id": exchange,
        "mode": result.get("mode", "dry_run"),
        "order_id": result.get("order_id", ""),
    }
    _execution_audit(
        state.portfolio_store, signal, accepted=True, reason=f"executed:{tick['mode']}"
    )
    state.log(f"tradingview execution: {tick}")
    return {"status": "executed", "executed": True, "tick": tick}
