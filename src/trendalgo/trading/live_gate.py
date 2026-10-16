"""The host's one live gate (H2).

Every live path asks this single truth table. Only a verified owner-signed go-live approval
can enable live orders. Env flags and the venue registry can only add conditions that must
also hold; they can never enable live on their own.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LiveRequest:
    """Facts the caller has already read. The gate decides; it does not look anything up."""

    requested_live: bool  # the caller wants a real order (dry_run is False)
    venue_enabled: bool  # the registry lists the venue as trading-enabled
    paused: bool  # the owner or an operator paused the venue
    owner_approved: bool  # set only by a verified owner-signed go-live command
    credentials_ok: bool  # venue API keys (CEX) or the DEX signer are present
    legal_ack_ok: bool  # a required ack is set (WORLDWIDE_TRADING_ACK, DEX_LIVE_TRADING_ACK)


@dataclass(frozen=True)
class LiveDecision:
    allowed: bool
    reason: str


def decide_live(request: LiveRequest) -> LiveDecision:
    """The one truth table. The first failing check names the refusal."""
    if request.paused:
        return LiveDecision(allowed=False, reason="paused")
    if not request.requested_live:
        return LiveDecision(allowed=True, reason="dry_run")
    if not request.venue_enabled:
        return LiveDecision(allowed=False, reason="venue_not_enabled")
    if not request.legal_ack_ok:
        return LiveDecision(allowed=False, reason="legal_ack_missing")
    if not request.owner_approved:
        return LiveDecision(allowed=False, reason="go_live_required")
    if not request.credentials_ok:
        return LiveDecision(allowed=False, reason="credentials_missing")
    return LiveDecision(allowed=True, reason="live_approved")
