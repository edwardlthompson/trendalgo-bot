"""Re-fit event taxonomy, severity, quiet hours, caps (NOTIF-02)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from enum import StrEnum
from typing import Any

EVENT_TAXONOMY: dict[str, dict[str, Any]] = {
    "regime_change": {
        "severity": "high",
        "payload": "old → new, votes, confidence, window",
    },
    "refit_proposed": {
        "severity": "medium",
        "payload": "params old → new, holdout evidence",
    },
    "refit_promoted": {
        "severity": "high",
        "payload": "shadow result, margin",
    },
    "refit_reverted": {
        "severity": "high",
        "payload": "losing window, revert target",
    },
    "param_diff": {
        "severity": "low",
        "payload": "single-quantile nudge, batched",
    },
}


class RefitNotifyMode(StrEnum):
    OFF = "off"
    ALL = "all"
    PROMOTION_REVERT_ONLY = "promotion_revert_only"


@dataclass(frozen=True)
class RefitNotifyPolicy:
    mode: RefitNotifyMode = RefitNotifyMode.ALL
    quiet_start: time | None = None
    quiet_end: time | None = None
    daily_cap: int = 20
    high_bypass_quiet: bool = True


def event_severity(event: str) -> str:
    meta = EVENT_TAXONOMY.get(event)
    return str(meta["severity"]) if meta else "low"


def in_quiet_hours(now: datetime, start: time | None, end: time | None) -> bool:
    if start is None or end is None:
        return False
    t = now.astimezone(UTC).timetz().replace(tzinfo=None)
    if start <= end:
        return start <= t < end
    # wraps midnight
    return t >= start or t < end


def should_emit(
    policy: RefitNotifyPolicy,
    *,
    event: str,
    now: datetime,
    sent_today: int,
) -> bool:
    if policy.mode is RefitNotifyMode.OFF:
        return False
    if policy.mode is RefitNotifyMode.PROMOTION_REVERT_ONLY and event not in {
        "refit_promoted",
        "refit_reverted",
    }:
        return False
    if sent_today >= policy.daily_cap:
        return False
    sev = event_severity(event)
    quiet = in_quiet_hours(now, policy.quiet_start, policy.quiet_end)
    if quiet:
        if policy.high_bypass_quiet and sev == "high":
            return True
        return False
    return True


def batch_cycle_message(events: list[tuple[str, str]]) -> str:
    """One message per cycle, maximum — all evidence in a single body."""
    if not events:
        return ""
    lines = ["EVENT: cycle batch"]
    for event, detail in events:
        sev = event_severity(event)
        payload = EVENT_TAXONOMY.get(event, {}).get("payload", "")
        lines.append(f"[{sev}] {event}: {detail} ({payload})")
    return "\n".join(lines)
