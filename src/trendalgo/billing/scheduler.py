"""Monthly statement + grace reminder jobs (M20)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from trendalgo.billing.engine import process_journal_trades
from trendalgo.billing.license_gate import advance_grace
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
    enrollment = billing.get_enrollment()
    if enrollment.get("enrolled") and result["rollup"]["license_fee_usd"] > 0:
        portfolio_store.insert_notification(
            "license",
            "Monthly license statement ready",
            f"Period {result['period']}: license ${result['rollup']['license_fee_usd']:.2f}. "
            "Pay from your wallet — view Billing tab.",
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
    billing.update_license_status(advanced)
    day = int(advanced.get("grace_day", 0))
    if day in (1, 4, 7):
        portfolio_store.insert_notification(
            "license",
            f"License grace day {day}",
            "User-initiated settlement required to restore live trading. No auto-withdraw.",
        )
        if on_log:
            on_log(f"grace reminder day {day}")
        return {"sent": 1, "grace_day": day}
    return {"sent": 0, "grace_day": day}
