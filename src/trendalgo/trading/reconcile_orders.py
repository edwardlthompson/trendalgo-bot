"""Settle the orders the journal cannot yet resolve, and record what each one executed (E3).

settle_orders reads the exchange in a fixed order: pending or unknown orders are found by client
id, the executed quantity of every order of ours that is not final is recorded, and the balances
are read last. An order still open on the exchange blocks the balance check. Orders without our
prefix are not ours; an unknown order with our prefix is an orphan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from trendalgo.trading.balance_check import BalanceMismatch
from trendalgo.trading.exchange_market import find_by_client_id
from trendalgo.trading.order_journal import OrderJournal

CLIENT_ID_PREFIX = "ta"
_LOOKBACK_MS = 60_000  # start each lookup a minute before the journal row was written
_FILL_TOLERANCE = 1e-8


@dataclass
class ReconcileReport:
    exchange: str
    settled: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    open: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    mismatches: list[BalanceMismatch] = field(default_factory=list)
    balance: dict[str, Any] = field(default_factory=dict)
    halt_reason: str | None = None


def settle_orders(journal: OrderJournal, client: Any, exchange: str) -> ReconcileReport:
    """Settle pending and unknown orders, record executed quantities, and read the balances.

    Changes no halt. reconcile_exchange adds the balance check and the halt.
    """
    report = ReconcileReport(exchange=exchange)
    for row in journal.unresolved(exchange):
        _settle(journal, client, row, report)
    open_orders = client.fetch_open_orders() or []
    for order in open_orders:
        client_id = str(order.get("clientOrderId") or "")
        if client_id.startswith(CLIENT_ID_PREFIX) and journal.get(client_id) is None:
            report.orphans.append(client_id)
    open_ids = {str(order.get("id")) for order in open_orders}
    for row in journal.unfinished(exchange):
        _record_fills(journal, client, row, open_ids)
    report.open = [row["client_id"] for row in journal.unfinished(exchange)]
    report.balance = client.fetch_balance() or {}
    return report


def _settle(
    journal: OrderJournal, client: Any, row: dict[str, Any], report: ReconcileReport
) -> None:
    since_ms = int(float(row["created_at"]) * 1000) - _LOOKBACK_MS
    found = find_by_client_id(client, row["pair"], row["client_id"], since_ms=since_ms)
    if found is None:
        report.unresolved.append(row["client_id"])
        return
    journal.set_status(
        row["client_id"],
        "submitted",
        exchange_order_id=str(found.get("id", "")),
        detail="settled by reconciliation",
    )
    report.settled.append(row["client_id"])


def _record_fills(
    journal: OrderJournal, client: Any, row: dict[str, Any], open_ids: set[str]
) -> None:
    """Record how much one order has executed. An order that is no longer open is final."""
    order_id = str(row["exchange_order_id"])
    order = client.fetch_order(order_id, row["pair"]) or {}
    filled = float(order.get("filled") or 0.0)
    if order_id in open_ids:
        status = "submitted"
    elif filled >= float(row["amount"]) - _FILL_TOLERANCE:
        status = "filled"
    else:
        status = "closed"
    journal.set_fills(row["client_id"], status, filled)
