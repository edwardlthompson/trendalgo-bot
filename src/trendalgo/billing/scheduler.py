"""Monthly statement + grace reminder jobs (M20, M8)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from trendalgo.billing.engine import poll_settlement_payments, process_journal_trades
from trendalgo.billing.license_gate import advance_grace, reminders_due
from trendalgo.billing.schema import GRACE_PERIOD_DAYS
from trendalgo.billing.store import BillingStore
from trendalgo.risk.journal import TradeJournal
from trendalgo.risk.manager import RiskManager


def run_monthly_statement_job(
    billing: BillingStore,
    journal: TradeJournal,
    risk_manager: RiskManager,
    portfolio_store: Any,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    result = process_journal_trades(billing, journal, risk_manager)
    if on_log:
        on_log(
            f"monthly statement: period={result['period']} fee=${result['rollup']['license_fee_usd']}"
        )
    if not billing.get_enrollment().get("enrolled"):
        return result
    for closed in result["finalized"]:
        fee = float(closed["license_fee_usd"])
        if fee > 0:  # only a month that closed in this run; the open month is not announced
            portfolio_store.insert_notification(
                "license",
                "Monthly license statement ready",
                f"Period {closed['period']}: license ${fee:.2f}. Pay from your wallet within "
                f"{GRACE_PERIOD_DAYS} days. Reminders on day 14 and day 25. View the Billing tab.",
            )
    return result


def run_grace_reminders(
    billing: BillingStore,
    portfolio_store: Any,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    status = billing.get_license_status()
    if not status.get("grace_started_at"):
        return {"sent": 0}
    advanced = advance_grace(status)
    day = int(advanced["grace_day"])
    due = reminders_due(day, status.get("last_reminder_day"))
    for reminder_day in due:
        portfolio_store.insert_notification(
            "license",
            f"License grace day {reminder_day} of {GRACE_PERIOD_DAYS}",
            "User-initiated settlement required to restore live trading. Never automatic withdrawal.",
        )
        if on_log:
            on_log(f"grace reminder day {reminder_day}")
    if due:
        advanced["last_reminder_day"] = due[-1]
    billing.update_license_status(advanced)
    return {"sent": len(due), "grace_day": day}


def run_payment_watch_job(
    billing: BillingStore,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    result = poll_settlement_payments(billing)
    if result.get("confirmed") and on_log:
        on_log(f"on-chain payments confirmed: {result['confirmed']}")
    return result
