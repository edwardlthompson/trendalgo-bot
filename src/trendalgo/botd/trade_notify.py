"""Send Telegram trade alerts from the host fill path (PC need not be running)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.botd.telegram_secrets import load_creds, trade_notify_allowed
from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.notifications.telegram_format import format_trade


def notify_fill(
    root: Path,
    *,
    pair: str,
    side: str,
    amount: float,
    price: float,
    fee_usd: float = 0.0,
    realized_pnl_usd: float = 0.0,
    plan_version: int = 0,
    live: bool = True,
    client: TelegramCommands | None = None,
) -> bool:
    """Return True when a message was sent (or dry-run client reported success)."""
    if not live or not trade_notify_allowed(root):
        return False
    token, chat_id = load_creds(root)
    tg = client or TelegramCommands(token=token, chat_id=chat_id)
    if not tg.enabled:
        return False
    text = format_trade(
        pair=pair,
        side=side,
        amount=amount,
        price=price,
        fee_usd=fee_usd,
        realized_pnl_usd=realized_pnl_usd,
        plan_version=plan_version,
    )
    return tg.send_message(text)


def outbox_payload(
    *,
    pair: str,
    side: str,
    amount: float,
    price: float,
    fee_usd: float,
    realized_pnl_usd: float,
    plan_version: int,
) -> dict[str, Any]:
    return {
        "kind": "trade_alert",
        "pair": pair,
        "side": side,
        "amount": amount,
        "price": price,
        "fee_usd": fee_usd,
        "realized_pnl_usd": realized_pnl_usd,
        "plan_version": plan_version,
    }
