"""Grace timeline, reminder schedule, and entry-only enforcement (M8, ADR-0017 decision 5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.billing.license_gate import (
    LicenseEntitlements,
    advance_grace,
    check_license_gate,
    clear_grace,
    reminders_due,
    start_grace_period,
)
from trendalgo.billing.scheduler import run_grace_reminders
from trendalgo.billing.schema import GRACE_PERIOD_DAYS, GRACE_REMINDER_DAYS
from trendalgo.billing.store import BillingStore

T0 = datetime(2026, 6, 1, tzinfo=UTC)
ENROLLED = {"enrolled": 1}


def _started(at: datetime) -> dict[str, Any]:
    return {
        "grace_started_at": at.isoformat(),
        "grace_day": 0,
        "suspended": 0,
        "unpaid_period": "2026-05",
        "last_reminder_day": 0,
    }


class _Inbox:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []

    def insert_notification(self, kind: str, title: str, body: str) -> None:
        self.items.append((kind, title, body))


def test_grace_is_thirty_days_with_reminders_on_days_0_14_and_25() -> None:
    assert GRACE_PERIOD_DAYS == 30
    assert GRACE_REMINDER_DAYS == (0, 14, 25)


def test_timeline_suspends_on_day_30_and_not_before() -> None:
    status = _started(T0)
    day_13 = advance_grace(status, now=T0 + timedelta(days=13, hours=23))
    assert (day_13["grace_day"], day_13["suspended"]) == (13, 0)
    day_29 = advance_grace(status, now=T0 + timedelta(days=29, hours=23))
    assert (day_29["grace_day"], day_29["suspended"]) == (29, 0)
    day_30 = advance_grace(status, now=T0 + timedelta(days=30))
    assert (day_30["grace_day"], day_30["suspended"]) == (30, 1)


def test_reminder_days_are_due_once_each() -> None:
    assert reminders_due(0, None) == [0]
    assert reminders_due(13, 0) == []
    assert reminders_due(14, 0) == [14]
    assert reminders_due(25, 14) == [25]
    assert reminders_due(40, 25) == []


def test_start_grace_is_day_zero_and_does_not_restart() -> None:
    started = start_grace_period({"grace_started_at": None, "suspended": 0}, "2026-06")
    assert started["grace_day"] == 0
    assert started["last_reminder_day"] == 0
    assert start_grace_period(started, "2026-07") is started


def test_gate_refuses_new_entries_after_thirty_days_but_never_exits() -> None:
    expired = _started(datetime.now(UTC) - timedelta(days=31))
    assert check_license_gate(ENROLLED, expired, dry_run=False) == (False, "license_suspended")
    context = {"enrollment": ENROLLED, "status": expired, "dry_run": False}
    entitlements = LicenseEntitlements()
    assert entitlements.check("enter", context) == (False, "license_suspended")
    for action in ("exit", "stop", "flatten"):
        assert entitlements.check(action, context) == (True, "ok")


def test_gate_allows_entries_inside_grace_and_when_paid() -> None:
    now = datetime.now(UTC)
    inside = _started(now - timedelta(days=29))
    assert check_license_gate(ENROLLED, inside, dry_run=False) == (True, "ok")
    paid = {
        **_started(now - timedelta(days=60)),
        "licensed_until": (now + timedelta(days=5)).isoformat(),
    }
    assert check_license_gate(ENROLLED, paid, dry_run=False) == (True, "licensed_until")


def test_clear_grace_resets_the_reminder_state() -> None:
    cleared = clear_grace(_started(T0))
    assert cleared["grace_started_at"] is None
    assert cleared["last_reminder_day"] is None
    assert cleared["suspended"] == 0


def test_reminder_job_sends_each_due_day_once(tmp_path) -> None:
    billing = BillingStore(tmp_path / "billing.db")
    inbox = _Inbox()
    billing.update_license_status(_started(datetime.now(UTC) - timedelta(days=15)))
    first = run_grace_reminders(billing, inbox)
    assert first["sent"] == 1
    assert "day 14" in inbox.items[0][1]
    second = run_grace_reminders(billing, inbox)
    assert second["sent"] == 0
    assert len(inbox.items) == 1
