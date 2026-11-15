"""Daily P/L notification formatter (P2, NT1)."""

from __future__ import annotations

import os
from typing import Any

from trendalgo.notifications.telegram import TelegramCommands


def format_daily_summary(overview: dict[str, Any]) -> str:
    net = float(overview.get("net_worth_usd", 0))
    daily = float(overview.get("daily_pnl_usd", 0))
    daily_pct = float(overview.get("daily_pnl_pct", 0)) * 100
    health = int(overview.get("health_score", 0))
    top = overview.get("allocation", [])
    mover = top[0]["asset"] if top else "—"
    insight = "Momentum positive" if daily >= 0 else "Consider rebalancing"
    if daily_pct > 2:
        insight = f"{mover} leading gains today"
    return (
        f"TrendAlgo daily portfolio\n"
        f"Net worth: ${net:,.2f}\n"
        f"Daily P/L: ${daily:+.2f} ({daily_pct:+.1f}%)\n"
        f"Health score: {health}/100\n"
        f"Insight: {insight}"
    )


def send_daily_notification(text: str, *, dry_run: bool = True) -> bool:
    from trendalgo.notifications.grokbot import telegram_ai_note

    body = telegram_ai_note(text)
    sent = False
    if not (dry_run and not os.environ.get("TELEGRAM_BOT_TOKEN")):
        sent = bool(TelegramCommands().send_message(body))
    _emit_grokbot_daily(body)
    return sent


def _emit_grokbot_daily(text: str) -> None:
    from trendalgo.notifications.grokbot import emit
    from trendalgo.notifications.grokbot_payload import envelope

    emit(envelope(event_type="daily_summary", reason=text))
