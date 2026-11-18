"""NOTIF-02: taxonomy, one message/cycle, quiet hours, daily cap, modes."""

from __future__ import annotations

from datetime import UTC, datetime, time

from trendalgo.notifications.refit_events import (
    EVENT_TAXONOMY,
    RefitNotifyMode,
    RefitNotifyPolicy,
    batch_cycle_message,
    should_emit,
)


def test_taxonomy_table_complete() -> None:
    expected = {
        "regime_change": "high",
        "refit_proposed": "medium",
        "refit_promoted": "high",
        "refit_reverted": "high",
        "param_diff": "low",
    }
    for event, severity in expected.items():
        assert event in EVENT_TAXONOMY
        assert EVENT_TAXONOMY[event]["severity"] == severity
        assert "payload" in EVENT_TAXONOMY[event]


def test_batching_one_message_for_five_change_cycle() -> None:
    events = [
        ("param_diff", "q nudged"),
        ("param_diff", "stop nudged"),
        ("param_diff", "atr nudged"),
        ("param_diff", "er nudged"),
        ("refit_proposed", "holdout +0.4"),
    ]
    msg = batch_cycle_message(events)
    assert isinstance(msg, str) and msg.startswith("EVENT: cycle batch")
    assert msg.count("EVENT:") == 1
    for _ev, detail in events:
        assert detail in msg


def test_quiet_hours_suppress_low_pass_high() -> None:
    policy = RefitNotifyPolicy(
        mode=RefitNotifyMode.ALL,
        quiet_start=time(22, 0),
        quiet_end=time(6, 0),
        daily_cap=10,
    )
    night = datetime(2026, 11, 11, 23, 0, tzinfo=UTC)
    assert should_emit(policy, event="param_diff", now=night, sent_today=0) is False
    assert should_emit(policy, event="refit_promoted", now=night, sent_today=0) is True


def test_daily_cap_and_promotion_only_mode() -> None:
    policy = RefitNotifyPolicy(mode=RefitNotifyMode.PROMOTION_REVERT_ONLY, daily_cap=1)
    day = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    assert should_emit(policy, event="refit_proposed", now=day, sent_today=0) is False
    assert should_emit(policy, event="refit_promoted", now=day, sent_today=0) is True
    assert should_emit(policy, event="refit_reverted", now=day, sent_today=1) is False
