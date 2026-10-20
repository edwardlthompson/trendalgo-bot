"""Every live order attempt must notify — silent live is forbidden (Phase 0)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class LiveOrderAttempt:
    exchange: str
    pair: str
    side: str
    amount: float
    dry_run: bool
    bot_id: int | None = None


AlertFn = Callable[[str, str], None]


def notify_live_order_attempt(attempt: LiveOrderAttempt, alert: AlertFn) -> bool:
    """Fire an alert for non-dry-run attempts. Returns True when an alert was sent."""
    if attempt.dry_run:
        return False
    title = "Live order attempt"
    body = f"{attempt.side.upper()} {attempt.amount} {attempt.pair} on {attempt.exchange}" + (
        f" (bot {attempt.bot_id})" if attempt.bot_id is not None else ""
    )
    alert(title, body)
    return True
