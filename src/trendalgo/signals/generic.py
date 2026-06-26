"""General-purpose signal webhook handler (T15)."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GenericSignalResult:
    accepted: bool
    reason: str
    signal: dict[str, Any] | None = None


class GenericSignalWebhook:
    def __init__(self, secret: str | None = None) -> None:
        self.secret = secret or os.environ.get("TRENDALGO_SIGNAL_SECRET", "")

    def handle(self, body: bytes, signature: str | None = None) -> GenericSignalResult:
        if not body:
            return GenericSignalResult(False, "empty body")
        if self.secret:
            expected = hashlib.sha256(self.secret.encode() + body).hexdigest()
            if signature != expected:
                return GenericSignalResult(False, "invalid signature")
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return GenericSignalResult(False, "invalid json")
        pair = str(payload.get("pair", ""))
        action = str(payload.get("action", "")).lower()
        if not pair or action not in ("buy", "sell", "close"):
            return GenericSignalResult(False, "missing pair or action")
        return GenericSignalResult(
            True,
            "ok",
            {"pair": pair, "action": action, "source": payload.get("source", "generic")},
        )
