"""Billing start delay — one month after first profitable trade."""

from __future__ import annotations

import calendar
from datetime import UTC, datetime
from typing import Any

from trendalgo.billing.schema import BILLING_START_DELAY_MONTHS
from trendalgo.billing.store import BillingStore
from trendalgo.risk.journal import TradeJournal


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def add_calendar_months(iso_ts: str, months: int = BILLING_START_DELAY_MONTHS) -> str:
    dt = datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    month = dt.month + months
    year = dt.year
    while month > 12:
        month -= 12
        year += 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day).isoformat()


def billing_is_active(enrollment: dict[str, Any], *, now: datetime | None = None) -> bool:
    starts = enrollment.get("billing_starts_at")
    if not starts:
        return False
    now = now or _utc_now()
    try:
        return now >= datetime.fromisoformat(str(starts))
    except ValueError:
        return False


def billable_from_iso(enrollment: dict[str, Any]) -> str | None:
    """Trades before this timestamp incur $0 license fee."""
    starts = enrollment.get("billing_starts_at")
    return str(starts) if starts else None


def eligibility_snapshot(
    enrollment: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    now = now or _utc_now()
    first_at = enrollment.get("first_profitable_trade_at")
    starts_at = enrollment.get("billing_starts_at")
    active = billing_is_active(enrollment, now=now)
    awaiting_first = not bool(first_at)
    trial = bool(first_at) and not active
    return {
        "first_profitable_trade_at": first_at,
        "billing_starts_at": starts_at,
        "billing_active": active,
        "awaiting_first_profit": awaiting_first,
        "trial_period": trial,
        "delay_months": BILLING_START_DELAY_MONTHS,
    }


def sync_billing_eligibility(billing: BillingStore, journal: TradeJournal) -> dict[str, Any]:
    enrollment = billing.get_enrollment()
    if enrollment.get("first_profitable_trade_at"):
        return enrollment
    first = journal.first_profitable_trade()
    if first is None:
        return enrollment
    first_at = str(first["created_at"])
    starts_at = add_calendar_months(first_at)
    billing.set_billing_eligibility(first_at, starts_at)
    return billing.get_enrollment()
