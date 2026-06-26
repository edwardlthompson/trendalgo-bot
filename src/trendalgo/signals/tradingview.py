"""TradingView webhook — HMAC, rate limit, IP allowlist, audit (T4)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from trendalgo.portfolio.db import PortfolioStore


@dataclass(frozen=True)
class WebhookResult:
    accepted: bool
    reason: str
    signal: dict[str, Any] | None = None


class TradingViewWebhook:
    def __init__(
        self,
        store: PortfolioStore,
        *,
        secret: str | None = None,
        allowlist: frozenset[str] | None = None,
        max_per_minute: int = 30,
    ) -> None:
        self.store = store
        self.secret = secret or os.environ.get("TRADINGVIEW_WEBHOOK_SECRET", "")
        raw = os.environ.get("TRADINGVIEW_IP_ALLOWLIST", "")
        self.allowlist = allowlist or frozenset(p.strip() for p in raw.split(",") if p.strip())
        self.max_per_minute = max_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _rate_limited(self, ip: str) -> bool:
        now = time.time()
        window = self._hits[ip]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.max_per_minute:
            return True
        window.append(now)
        return False

    def _audit(self, ip: str, payload: bytes, accepted: bool, reason: str) -> None:
        digest = hashlib.sha256(payload).hexdigest()
        self.store.insert_webhook_audit(
            client_ip=ip,
            payload_hash=digest,
            accepted=accepted,
            reason=reason,
        )

    def _verify_hmac(self, payload: bytes, signature: str | None) -> bool:
        if not self.secret:
            return False
        if not signature:
            return False
        expected = hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature.strip())

    def handle(
        self,
        payload: bytes,
        *,
        client_ip: str,
        signature: str | None = None,
    ) -> WebhookResult:
        if self.allowlist and client_ip not in self.allowlist:
            self._audit(client_ip, payload, False, "ip not allowlisted")
            return WebhookResult(False, "ip not allowlisted")

        if self._rate_limited(client_ip):
            self._audit(client_ip, payload, False, "rate limit")
            return WebhookResult(False, "rate limit exceeded")

        if not self._verify_hmac(payload, signature):
            self._audit(client_ip, payload, False, "invalid hmac")
            return WebhookResult(False, "invalid signature")

        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._audit(client_ip, payload, False, "invalid json")
            return WebhookResult(False, "invalid json")

        if not isinstance(data, dict):
            self._audit(client_ip, payload, False, "invalid payload")
            return WebhookResult(False, "invalid payload")

        signal = {
            "pair": str(data.get("pair", data.get("ticker", ""))),
            "action": str(data.get("action", data.get("signal", ""))).lower(),
            "source": "tradingview",
        }
        self._audit(client_ip, payload, True, "accepted")
        return WebhookResult(True, "accepted", signal=signal)
