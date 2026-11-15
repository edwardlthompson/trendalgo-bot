"""Send Telegram trade alerts first, then optional Grok Bot webhook."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.botd.telegram_secrets import load_creds, trade_notify_allowed
from trendalgo.notifications.grokbot import emit, telegram_ai_note
from trendalgo.notifications.grokbot_payload import trade_payload
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
    strategy_id: str | None = None,
    rationale: str | None = None,
    exit_rule: str | None = None,
    exchange: str | None = None,
) -> bool:
    """Telegram first and independently; Grok Bot never waits or gates the send."""
    text = format_trade(
        pair=pair,
        side=side,
        amount=amount,
        price=price,
        fee_usd=fee_usd,
        realized_pnl_usd=realized_pnl_usd,
        plan_version=plan_version,
        strategy_id=strategy_id,
        rationale=rationale,
        exit_rule=exit_rule,
    )
    text = telegram_ai_note(text)
    _append_device_trade_alert(root, pair=pair, reason=text)
    payload = trade_payload(
        pair=pair,
        side=side,
        amount=amount,
        price=price,
        realized_pnl_usd=realized_pnl_usd,
        strategy_id=strategy_id,
        rationale=rationale,
        exit_rule=exit_rule,
        exchange=exchange,
        plan_version=plan_version,
    )
    sent = False
    if live and trade_notify_allowed(root):
        token, chat_id = load_creds(root)
        tg = client or TelegramCommands(token=token, chat_id=chat_id)
        if tg.enabled:
            from trendalgo.notifications.grokbot_explain import why_markup

            sent = bool(tg.send_message(text, reply_markup=why_markup(payload)))
    emit(payload)
    return sent


def _append_device_trade_alert(root: Path, *, pair: str, reason: str) -> None:
    """Bridge fills into device Alerts → Trades (best-effort)."""
    try:
        from trendalgo.device.scanner_alert_diff import AlertEvent
        from trendalgo.device.scanner_alerts_store import append_alerts

        symbol = pair.split("/", 1)[0].upper() if pair else ""
        append_alerts(
            root,
            [AlertEvent(kind="trade_alert", symbol=symbol, pair=pair, reason=reason)],
        )
    except (OSError, ValueError, TypeError, ImportError):
        return


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
