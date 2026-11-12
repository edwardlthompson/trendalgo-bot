"""BILL-05: monotonic grace day = max(clock, stored)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trendalgo.billing.license_gate import advance_grace, grace_days_elapsed, monotonic_grace_day

T0 = datetime(2026, 6, 1, tzinfo=UTC)


def test_clock_rewind_does_not_extend_grace() -> None:
    status = {
        "grace_started_at": T0.isoformat(),
        "grace_day": 10,
        "max_grace_day": 10,
        "suspended": 0,
    }
    # Host clock rewound to day 3
    advanced = advance_grace(status, now=T0 + timedelta(days=3))
    assert advanced["grace_day"] == 10
    assert advanced["max_grace_day"] == 10
    assert advanced["suspended"] == 0


def test_forward_jump_advances_but_does_not_skip_suspension() -> None:
    status = {
        "grace_started_at": T0.isoformat(),
        "grace_day": 5,
        "max_grace_day": 5,
        "suspended": 0,
    }
    advanced = advance_grace(status, now=T0 + timedelta(days=31))
    assert advanced["grace_day"] == 31
    assert advanced["max_grace_day"] == 31
    assert advanced["suspended"] == 1


def test_monotonic_helper() -> None:
    assert monotonic_grace_day(clock_day=2, stored_day=7) == 7
    assert monotonic_grace_day(clock_day=9, stored_day=7) == 9
    assert grace_days_elapsed({"grace_started_at": T0.isoformat()}, T0 + timedelta(days=4)) == 4
