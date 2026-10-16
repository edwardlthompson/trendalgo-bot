"""Gate new buys on a clean reconciliation, and check the exchange balances (E3).

Before every new buy, and on each balance sync, the exchange is settled (reconcile_orders) and
the balances are compared with the expected positions (balance_check). An orphan order or an
unexplained balance change halts the exchange. Exits (sells) are never refused here (R5).
"""

from __future__ import annotations

from typing import Any

from trendalgo.trading.balance_check import (
    balance_total,
    check_balances,
    fill_flows,
    take_checkpoint,
)
from trendalgo.trading.order_journal import (
    OrderHaltedError,
    OrderJournal,
    OrderOutcomeUnknownError,
)
from trendalgo.trading.reconcile_orders import ReconcileReport, settle_orders


def reconcile_exchange(
    journal: OrderJournal, client: Any, exchange: str, watch: tuple[str, ...] = ()
) -> ReconcileReport:
    """Settle, then check the watched assets and every asset our orders have touched."""
    report = settle_orders(journal, client, exchange)
    if report.orphans:
        report.halt_reason = "orphan order(s) on the exchange: " + ", ".join(report.orphans)
    elif not report.unresolved and not report.open:
        report.mismatches = check_balances(journal, report.balance, exchange, set(watch))
        if report.mismatches:
            report.halt_reason = "unexplained balance change: " + "; ".join(
                mismatch.describe() for mismatch in report.mismatches
            )
    if report.halt_reason:
        journal.halt(exchange, report.halt_reason)
    return report


def ensure_clear_for_buy(
    journal: OrderJournal, client: Any, exchange: str, pair: str | None = None
) -> None:
    """Raise unless a new buy is safe: not halted, nothing unsettled, and balances explained."""
    if journal.is_halted(exchange):
        raise OrderHaltedError(f"{exchange}: new buys are halted; review the reason, then reset")
    watch = (pair.split("/")[0],) if pair else ()
    try:
        report = reconcile_exchange(journal, client, exchange, watch)
    except Exception as exc:
        raise OrderOutcomeUnknownError(f"{exchange}: reconciliation failed; buy not sent") from exc
    if report.orphans:
        raise OrderHaltedError(f"{exchange}: orphan order found on the exchange; buys halted")
    if report.mismatches:
        raise OrderHaltedError(f"{exchange}: {report.halt_reason}; buys halted")
    if report.unresolved:
        raise OrderOutcomeUnknownError(
            f"{exchange}: {len(report.unresolved)} earlier order(s) unresolved; buy not sent"
        )
    if report.open:
        raise OrderOutcomeUnknownError(
            f"{exchange}: {len(report.open)} earlier order(s) still open; buy not sent"
        )


def accept_balance(journal: OrderJournal, client: Any, exchange: str, asset: str) -> float:
    """Operator action: take the holding the exchange shows as the new expected position.

    Use after reviewing an unexplained change, such as a deposit. Refuses while any order of ours
    is unsettled or an orphan exists. It does not clear the halt; call journal.reset_halt for that.
    """
    report = settle_orders(journal, client, exchange)
    if report.orphans or report.unresolved or report.open:
        raise OrderOutcomeUnknownError(f"{exchange}: settle earlier orders before accepting")
    total = balance_total(report.balance, asset)
    flow = fill_flows(journal, exchange).get(asset, 0.0)
    take_checkpoint(journal, exchange, asset, total, flow)
    return total
