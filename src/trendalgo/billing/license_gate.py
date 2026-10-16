"""License gate — grace period and live trading suspension (M10, M20)."""

from __future__ import annotations

import calendar
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from trendalgo.billing.schema import GRACE_PERIOD_DAYS, GRACE_REMINDER_DAYS

EXIT_ACTIONS = frozenset({"exit", "stop", "flatten"})


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
    if not _grace_suspended(status, datetime.now(UTC)):
        return True, "ok"
    return False, "license_suspended"


class Entitlements(Protocol):
    """ADR-0017 port. The host asks before it acts. It is consulted for new entries only."""

    def check(self, action: str, context: Mapping[str, Any]) -> tuple[bool, str]: ...


class LicenseEntitlements:
    """Adapter over check_license_gate, which keeps its reason codes. Exits are never gated."""

    def check(self, action: str, context: Mapping[str, Any]) -> tuple[bool, str]:
        if action in EXIT_ACTIONS:
            return True, "ok"
        if action != "enter":
            return False, "unknown_action"  # fail closed for anything the port does not know
        enrollment = context.get("enrollment")
        status = context.get("status")
        dry_run = context.get("dry_run")
        # Missing facts must refuse. Without them, check_license_gate would read "free_tier".
        if not isinstance(enrollment, Mapping) or not isinstance(status, Mapping):
            return False, "missing_context"
        if not isinstance(dry_run, bool):
            return False, "missing_context"
        return check_license_gate(dict(enrollment), dict(status), dry_run=dry_run)


def _parse_utc(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def grace_days_elapsed(status: dict[str, Any], now: datetime) -> int | None:
    """Whole days since the grace started, or None when no readable start is stored."""
    started = _parse_utc(status.get("grace_started_at"))
    return None if started is None else max(0, (now - started).days)


def _grace_suspended(status: dict[str, Any], now: datetime) -> bool:
    """Computed from the start time, so a job that did not run cannot extend the grace."""
    elapsed = grace_days_elapsed(status, now)
    if elapsed is None:
        return bool(status.get("suspended"))
    return elapsed >= GRACE_PERIOD_DAYS


def reminders_due(day: int, last_sent_day: int | None) -> list[int]:
    """Reminder days reached since the last one sent (day 0 is sent when the grace starts)."""
    last = -1 if last_sent_day is None else last_sent_day
    return [d for d in GRACE_REMINDER_DAYS if last < d <= day]


def start_grace_period(status: dict[str, Any], unpaid_period: str) -> dict[str, Any]:
    if status.get("grace_started_at"):
        return status
    now = _utc_now()
    return {
        **status,
        "grace_started_at": now,
        "grace_day": 0,
        "suspended": 0,
        "unpaid_period": unpaid_period,
        "last_reminder_day": 0,  # the statement notice is the day-0 reminder
        "updated_at": now,
    }


def advance_grace(status: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    elapsed = grace_days_elapsed(status, now or datetime.now(UTC))
    day = elapsed if elapsed is not None else int(status.get("grace_day", 0))
    return {
        **status,
        "grace_day": day,
        "suspended": int(day >= GRACE_PERIOD_DAYS),
        "updated_at": _utc_now(),
    }


def clear_grace(status: dict[str, Any]) -> dict[str, Any]:
    return {
        **status,
        "grace_started_at": None,
        "grace_day": 0,
        "suspended": 0,
        "unpaid_period": None,
        "last_reminder_day": None,
        "updated_at": _utc_now(),
    }
