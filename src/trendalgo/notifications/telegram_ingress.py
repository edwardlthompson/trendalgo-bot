"""Validated, rate-limited Telegram webhook ingress."""

from __future__ import annotations

import hmac
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.risk.manager import RiskManager


@dataclass
class TelegramIngress:
    """Translate Telegram updates into existing command-handler calls."""

    commands: TelegramCommands = field(default_factory=TelegramCommands)
    _hits: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _allowed_chat_ids(self) -> frozenset[str]:
        raw = os.environ.get("TELEGRAM_CHAT_ID", "")
        return frozenset(value.strip() for value in raw.split(",") if value.strip())

    def _rate_limited(self, chat_id: str) -> bool:
        with self._lock:
            now = time.monotonic()
            window = self._hits[chat_id]
            while window and now - window[0] >= 60:
                window.popleft()
            try:
                limit = max(1, int(os.environ.get("TELEGRAM_RATE_LIMIT_PER_MINUTE", "10")))
            except ValueError:
                limit = 10
            if len(window) >= limit:
                return True
            window.append(now)
            return False

    def handle(
        self,
        update: dict[str, Any],
        manager: RiskManager,
        *,
        secret: str | None,
    ) -> tuple[int, dict[str, Any]]:
        expected_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
        if expected_secret and (secret is None or not hmac.compare_digest(secret, expected_secret)):
            return 403, {"accepted": False, "reason": "invalid webhook secret"}

        message = update.get("message")
        if not isinstance(message, dict):
            return 400, {"accepted": False, "reason": "missing message"}
        chat = message.get("chat")
        text = message.get("text")
        if not isinstance(chat, dict) or not isinstance(text, str):
            return 400, {"accepted": False, "reason": "invalid message"}

        chat_id = str(chat.get("id", ""))
        allowed = self._allowed_chat_ids()
        if not allowed:
            return 503, {"accepted": False, "reason": "telegram ingress not configured"}
        if chat_id not in allowed:
            return 403, {"accepted": False, "reason": "chat not allowlisted"}
        if self._rate_limited(chat_id):
            return 429, {"accepted": False, "reason": "rate limit exceeded"}

        reply = self.commands.handle(text, manager)
        sent = self.commands.send_message(reply)
        return 200, {"accepted": True, "reply": reply, "sent": sent}
