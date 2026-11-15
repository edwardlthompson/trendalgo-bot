"""Which Grok Bot events to send (quota control)."""

from __future__ import annotations

import os

EVENTS_ENV = "GROKBOT_WEBHOOK_EVENTS"
DEFAULT_EVENTS = "all"

_TRADE = frozenset({"trade_entry", "trade_exit", "trades", "trade"})
_SCANNER_A = frozenset({"scanner-a", "scanner_a", "scanner-a-tier"})


def event_tokens() -> frozenset[str]:
    raw = os.environ.get(EVENTS_ENV, DEFAULT_EVENTS).strip().lower()
    if not raw:
        return frozenset({DEFAULT_EVENTS})
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def event_allowed(event_type: str, *, tier: str | None = None) -> bool:
    """Filter POSTs. ``test`` always passes when the channel is enabled."""
    kind = str(event_type or "").strip().lower()
    if kind in {"test", "explain_request"}:
        return True
    tokens = event_tokens()
    if not tokens or "all" in tokens:
        return True
    if kind in tokens:
        if kind == "scanner_alert":
            return _scanner_tier_ok(tokens, tier)
        return True
    if kind in {"trade_entry", "trade_exit"} and tokens & _TRADE:
        return True
    if kind == "weekly_digest" and tokens & {"weekly", "weekly_digest"}:
        return True
    if kind == "scanner_alert":
        if "scanner" in tokens:
            return True
        if tokens & _SCANNER_A:
            return (tier or "").strip().upper() == "A"
    return False


def _scanner_tier_ok(tokens: frozenset[str], tier: str | None) -> bool:
    if tokens & _SCANNER_A and "scanner" not in tokens:
        return (tier or "").strip().upper() == "A"
    return True
