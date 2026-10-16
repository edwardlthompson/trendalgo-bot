"""Owner commands from the device (ADR-0016 POST /api/v1/commands)."""

from __future__ import annotations

from typing import Any

ALLOWED = frozenset({"pause", "resume", "delete", "force_buy", "force_sell", "flatten"})


def parse_command(body: dict[str, Any]) -> tuple[str, str, str]:
    """Return (action, bot_id, idempotency_key). Raises ValueError on bad input."""
    action = str(body.get("action") or "").strip().lower()
    if action not in ALLOWED:
        raise ValueError(
            "action must be one of: pause, resume, delete, force_buy, force_sell, flatten"
        )
    bot_id = str(body.get("bot_id") or "").strip()
    if not bot_id:
        raise ValueError("bot_id is required")
    key = str(body.get("idempotency_key") or "").strip()
    if not key:
        raise ValueError("idempotency_key is required")
    return action, bot_id, key


def apply_command(
    *,
    action: str,
    bot_id: str,
    idempotency_key: str,
    outbox: Any,
    owner_id: str,
    now: int,
) -> dict[str, Any]:
    """Record the command as an outbox event for the runner / device ack path."""
    dedupe = f"cmd:{idempotency_key}"
    enqueued = outbox.enqueue(
        owner_id=owner_id,
        dedupe_key=dedupe,
        kind="command",
        payload={"action": action, "bot_id": bot_id, "idempotency_key": idempotency_key},
        now=now,
    )
    return {
        "accepted": True,
        "action": action,
        "bot_id": bot_id,
        "idempotency_key": idempotency_key,
        "duplicate": not enqueued,
    }
