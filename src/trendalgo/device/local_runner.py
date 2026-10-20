"""Optional device-local dry-run / live tick (Phase 3). Live still needs go-live."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trendalgo.trading.live_gate import LiveDecision, LiveRequest, decide_live


@dataclass(frozen=True)
class DeviceTickResult:
    mode: str
    blocked: str | None = None


def device_tick_allowed(
    *,
    venue: str,
    disclosure_accepted: bool,
    dry_run: bool,
    go_live_approved: bool,
    credentials_ok: bool,
    paused: bool,
) -> DeviceTickResult:
    """Device venue dry-run ticks are allowed; live still goes through LiveGate."""
    if venue != "device":
        return DeviceTickResult(mode="host_only", blocked="venue_is_host")
    if not disclosure_accepted:
        return DeviceTickResult(mode="blocked", blocked="disclosure_required")
    if dry_run:
        return DeviceTickResult(mode="dry_run")
    decision = decide_live(
        LiveRequest(
            requested_live=True,
            venue_enabled=True,
            paused=paused,
            owner_approved=go_live_approved,
            credentials_ok=credentials_ok,
            legal_ack_ok=True,
        )
    )
    if not decision.allowed:
        return DeviceTickResult(mode="blocked", blocked=decision.reason)
    return DeviceTickResult(mode="live_approved")


def live_decision_dict(decision: LiveDecision) -> dict[str, Any]:
    return {"allowed": decision.allowed, "reason": decision.reason}
