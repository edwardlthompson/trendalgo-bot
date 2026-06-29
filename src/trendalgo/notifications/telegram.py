"""Telegram command handler (H-008 — requires .env tokens)."""

from __future__ import annotations

import os
from urllib import error, parse, request

from trendalgo.risk.manager import RiskManager
from trendalgo.risk.metrics import metrics_summary


class TelegramCommands:
    """Status / pause / resume for dry-run bot."""

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
        if cmd in ("/resume", "resume"):
            manager.resume()
            return "Trading resumed"
        if cmd in ("/help", "help"):
            return "Commands: status, pause, resume"
        return "Unknown command — try: status, pause, resume"

    def send_message(self, text: str) -> bool:
        if not self.enabled or not self.token or not self.chat_id:
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = parse.urlencode({"chat_id": self.chat_id, "text": text}).encode()
        try:
            req = request.Request(url, data=data, method="POST")
            with request.urlopen(req, timeout=15) as resp:
                return int(resp.status) == 200
        except (error.URLError, TimeoutError):
            return False

    def notify_trade(self, pair: str, side: str, pnl_usd: float) -> bool:
        return self.send_message(f"Trade {side} {pair} pnl=${pnl_usd:.2f}")
