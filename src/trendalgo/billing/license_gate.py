"""License gate — grace period and live trading suspension (M10, M20)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from trendalgo.billing.schema import GRACE_PERIOD_DAYS


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
