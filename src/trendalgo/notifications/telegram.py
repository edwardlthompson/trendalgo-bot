"""Telegram command handler (H-008 — requires .env tokens)."""

from __future__ import annotations

import json
import os
from urllib import error, parse, request

from trendalgo.risk.manager import RiskManager
from trendalgo.risk.metrics import metrics_summary

_HOST_ONLY = frozenset({"/resume", "resume", "/reset", "reset", "/reset_breaker", "reset_breaker"})


class TelegramCommands:
    """Status and pause. Resume and breaker reset are refused here (H6)."""

    def __init__(
        self,
        token: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)

    def handle(self, command: str, manager: RiskManager) -> str:
        cmd = command.strip().lower()
        if cmd in ("/status", "status"):
            m = metrics_summary(manager)
            return (
                f"TrendAlgo status\n"
                f"equity=${m['equity_usd']} daily_pnl=${m['daily_pnl_usd']}\n"
                f"drawdown={m['drawdown_pct'] * 100:.1f}% can_trade={m['can_trade']}"
            )
        if cmd in ("/pause", "pause"):
            manager.pause()
            return "Trading paused"
        if cmd in _HOST_ONLY:
            # H6: Telegram can pause and nothing else. Resume and breaker reset stay on the host.
            return "Refused: Telegram can pause only. Resume and breaker reset run on the host."
        if cmd in ("/help", "help"):
            return "Commands: status, pause. Resume and breaker reset are host-only."
        return "Unknown command — try: status, pause"

    def send_message(self, text: str) -> bool:
        if not self.enabled or not self.token or not self.chat_id:
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = parse.urlencode({"chat_id": self.chat_id, "text": text}).encode()
        try:
            req = request.Request(url, data=data, method="POST")
            with request.urlopen(req, timeout=15) as resp:
                return int(resp.status) == 200
        except (error.URLError, TimeoutError, OSError):
            return False

    def send_photo(self, png: bytes, caption: str = "") -> bool:
        """Multipart sendPhoto. Falls back to send_message when png is empty."""
        if not self.enabled or not self.token or not self.chat_id:
            return False
        if not png:
            return self.send_message(caption or "(chart unavailable)")
        boundary = "----TrendAlgoBoundary7MA4YWxkTrZu0gW"
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        parts: list[bytes] = []
        for name, value in (("chat_id", self.chat_id), ("caption", caption[:1024])):
            parts.append(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode()
            )
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="photo"; filename="chart.png"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode()
        )
        parts.append(png)
        parts.append(f"\r\n--{boundary}--\r\n".encode())
        body = b"".join(parts)
        try:
            req = request.Request(
                url,
                data=body,
                method="POST",
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
            with request.urlopen(req, timeout=30) as resp:
                return int(resp.status) == 200
        except (error.URLError, TimeoutError, OSError):
            return self.send_message(caption) if caption else False

    def api_url(self, method: str) -> str | None:
        if not self.token:
            return None
        return f"https://api.telegram.org/bot{self.token}/{method}"

    def delete_webhook(self) -> bool:
        """Clear webhook so getUpdates works (noop success if already clear)."""
        payload = self._api_json("deleteWebhook", http="POST")
        return bool(payload and payload.get("ok"))

    def detect_chat_id(self) -> str | None:
        """deleteWebhook then last private chat from getUpdates (user must /start first)."""
        if not self.token:
            return None
        if not self.delete_webhook():
            return None
        payload = self._api_json("getUpdates", http="GET")
        if not payload:
            return None
        results = payload.get("result")
        if not isinstance(results, list):
            return None
        for item in reversed(results):
            if not isinstance(item, dict):
                continue
            msg = item.get("message")
            if not isinstance(msg, dict):
                continue
            chat = msg.get("chat")
            if isinstance(chat, dict) and chat.get("id") is not None:
                return str(chat["id"])
        return None

    def _api_json(self, method: str, *, http: str) -> dict[str, object] | None:
        url = self.api_url(method)
        if not url:
            return None
        try:
            req = request.Request(url, method=http, data=b"" if http == "POST" else None)
            with request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
        except (error.URLError, TimeoutError, OSError, UnicodeDecodeError):
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def notify_trade(self, pair: str, side: str, pnl_usd: float) -> bool:
        return self.send_message(f"Trade {side} {pair} pnl=${pnl_usd:.2f}")
