"""In-process Grok Bot cooldown after quota/timeout (no retry spam)."""

from __future__ import annotations

import os
import time

COOLDOWN_ENV = "GROKBOT_WEBHOOK_COOLDOWN_SEC"
DEFAULT_COOLDOWN_SEC = 900.0

_until = 0.0


def cooldown_seconds() -> float:
    raw = os.environ.get(COOLDOWN_ENV, "").strip()
    if not raw:
        return DEFAULT_COOLDOWN_SEC
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_COOLDOWN_SEC


def is_unavailable() -> bool:
    return time.monotonic() < _until


def mark_unavailable() -> None:
    global _until
    _until = time.monotonic() + cooldown_seconds()


def reset() -> None:
    """Tests only."""
    global _until
    _until = 0.0


def remaining_seconds() -> float:
    return max(0.0, _until - time.monotonic())
