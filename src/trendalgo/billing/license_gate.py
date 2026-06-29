"""License gate — grace period and live trading suspension (M10, M20)."""

from __future__ import annotations

import calendar
from datetime import UTC, datetime
from typing import Any

from trendalgo.billing.schema import GRACE_PERIOD_DAYS


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def licensed_until_for_period(period: str) -> str:
    """End of the calendar month following the paid statement period (UTC)."""
    year, month = (int(x) for x in period.split("-"))
    if month == 12:
        end_year, end_month = year + 1, 1
    else:
        end_year, end_month = year, month + 1
    last_day = calendar.monthrange(end_year, end_month)[1]
    end = datetime(end_year, end_month, last_day, 23, 59, 59, tzinfo=UTC)
    return end.isoformat()


def _is_future(iso_ts: str) -> bool:
    try:
        return datetime.fromisoformat(iso_ts) > datetime.now(UTC)
    except ValueError:
        return False


def check_license_gate(
    enrollment: dict[str, Any],
    status: dict[str, Any],
    *,
    dry_run: bool,
) -> tuple[bool, str]:
    if dry_run:
        return True, "dry_run"
    if not enrollment.get("enrolled"):
        return True, "free_tier"
    licensed_until = status.get("licensed_until")
    if licensed_until and _is_future(str(licensed_until)):
        return True, "licensed_until"
    if not status.get("suspended"):
        return True, "ok"
    return False, "license_suspended"


def start_grace_period(status: dict[str, Any], unpaid_period: str) -> dict[str, Any]:
    if status.get("grace_started_at"):
        return status
    return {
        **status,
        "grace_started_at": _utc_now(),
        "grace_day": 1,
        "suspended": 0,
        "unpaid_period": unpaid_period,
        "updated_at": _utc_now(),
    }


def advance_grace(status: dict[str, Any]) -> dict[str, Any]:
    day = int(status.get("grace_day", 0)) + 1
    suspended = day > GRACE_PERIOD_DAYS
    return {
        **status,
        "grace_day": day,
        "suspended": int(suspended),
        "updated_at": _utc_now(),
    }


def clear_grace(status: dict[str, Any]) -> dict[str, Any]:
    return {
        **status,
        "grace_started_at": None,
        "grace_day": 0,
        "suspended": 0,
        "unpaid_period": None,
        "updated_at": _utc_now(),
    }
