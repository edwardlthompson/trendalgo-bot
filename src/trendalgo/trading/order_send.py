"""Send one market order and settle its outcome in the order journal (E2, E3).

A refused order is recorded and counts toward the halt. A lost reply is never re-sent: the order
is looked up by client id first, and if it cannot be found the outcome stays unknown.
"""

from __future__ import annotations

from typing import Any

import ccxt

from trendalgo.trading.exchange_market import find_by_client_id
from trendalgo.trading.order_journal import OrderJournal, OrderOutcomeUnknownError


def send_market_order(
    exchange: Any,
    journal: OrderJournal,
    exchange_id: str,
    client_id: str,
    pair: str,
    side: str,
    amount: float,
) -> dict[str, Any]:
    """Place one market order under its client id, and return the order the exchange reports."""
    try:
        order = exchange.create_order(
            pair, "market", side, amount, params=order_params(exchange_id, client_id)
        )
    except ccxt.ExchangeError as exc:  # refused by the exchange: nothing was placed
        journal.set_status(client_id, "rejected", detail=str(exc))
        journal.record_failure(exchange_id, str(exc))
        raise
    except Exception as exc:  # timeout or dropped connection: the outcome is unknown
        return _resolve_unknown(exchange, journal, exchange_id, client_id, pair, exc)
    journal.set_status(client_id, "submitted", exchange_order_id=str(order.get("id")))
    journal.record_success(exchange_id)
    return dict(order)


def order_params(exchange_id: str, client_id: str) -> dict[str, Any]:
    """Client id on every order, plus Kraken's quote-currency fee flag (E3).

    With the fee in quote currency, a fill moves the base balance by exactly its quantity.
    """
    params: dict[str, Any] = {"clientOrderId": client_id}
    if exchange_id == "kraken":
        params["oflags"] = "fciq"
    return params


def _resolve_unknown(
    exchange: Any,
    journal: OrderJournal,
    exchange_id: str,
    client_id: str,
    pair: str,
    exc: Exception,
) -> dict[str, Any]:
    """Look the order up before anything else. A blind re-send could double the position."""
    try:
        found = find_by_client_id(exchange, pair, client_id)
    except Exception:  # the lookup failed too; the order is still not confirmed
        found = None
    if found is None:
        detail = f"outcome unknown after {type(exc).__name__}: {exc}"
        journal.set_status(client_id, "unknown", detail=detail)
        journal.record_failure(exchange_id, detail)
        raise OrderOutcomeUnknownError(
            f"{exchange_id}: order {client_id} may have been placed; reconcile before sending again"
        ) from exc
    journal.set_status(
        client_id,
        "submitted",
        exchange_order_id=str(found.get("id", "")),
        detail="recovered by lookup after an error",
    )
    journal.record_success(exchange_id)
    return found
