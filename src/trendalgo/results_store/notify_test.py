"""Telegram / Grokbot delivery tests for Avalonia Alerts & Settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.grokbot_notify import send_device_test
from trendalgo.device.notify_prefs import load_prefs, save_prefs
from trendalgo.device.profile import SETTINGS_FILE
from trendalgo.device.telegram_vault import load_telegram_creds
from trendalgo.notifications.telegram import TelegramCommands


def _mask_chat(chat: str) -> str:
    s = chat.strip()
    if len(s) <= 4:
        return "***"
    return f"{s[:2]}***{s[-2:]}"


def send_telegram_test(root: Path) -> dict[str, Any]:
    token, chat = load_telegram_creds()
    if not token or not chat:
        return {
            "ok": False,
            "configured": False,
            "error": "missing_creds",
            "detail": "Telegram bot token or chat ID missing in Windows CredMan.",
        }
    prefs = load_prefs(root)
    tg = TelegramCommands(token=token, chat_id=chat)
    text = "<b>TrendAlgo</b> — Telegram notification test succeeded."
    ok, detail = tg.send_message_detailed(text, parse_mode="HTML")
    if ok and not prefs.telegram_enabled:
        prefs.telegram_enabled = True
        save_prefs(root, prefs)
    return {
        "ok": ok,
        "configured": True,
        "chat_hint": _mask_chat(chat),
        "error": None if ok else (detail or "send_failed"),
        "detail": None if ok else detail,
    }


def send_grokbot_test(root: Path) -> dict[str, Any]:
    ok, detail = send_device_test(root / SETTINGS_FILE)
    return {"ok": bool(ok), "error": None if ok else str(detail)}


def send_telegram_rich_preview(root: Path) -> dict[str, Any]:
    """Send a full candlestick + ranked-strategies PNG + HTML caption + inline buttons preview."""
    token, chat = load_telegram_creds()
    if not token or not chat:
        return {
            "ok": False,
            "configured": False,
            "error": "missing_creds",
            "detail": "Telegram bot token or chat ID missing in Windows CredMan.",
        }
    from trendalgo.device.alert_preview import sample_event
    from trendalgo.device.lts_scan_model import load_lts_rows
    from trendalgo.notifications.telegram_alert_enrich import enrich_enter_coin
    from trendalgo.notifications.telegram_chart import enter_alert_png
    from trendalgo.notifications.telegram_format import format_qualified_enter
    from trendalgo.notifications.telegram_keyboard import reply_markup_json

    rows = [r for r in load_lts_rows(root, lane="crypto") if isinstance(r, dict)]
    coin: dict[str, Any] | None = next(
        (r for r in rows if r.get("backtest_top_strategies")), rows[0] if rows else None
    )
    if coin is None:
        ev = sample_event("entered")
        coin = ev.coin if isinstance(ev.coin, dict) else {"symbol": "BTC", "pair": "BTC/USD"}
    enriched = enrich_enter_coin(coin)
    caption = format_qualified_enter(enriched)
    markup = reply_markup_json(enriched)
    png = enter_alert_png(enriched)
    tg = TelegramCommands(token=token, chat_id=chat)
    if png:
        ok = bool(tg.send_photo(png, caption, parse_mode="HTML", reply_markup=markup))
        detail = None if ok else "send_photo_failed"
    else:
        ok, detail = tg.send_message_detailed(caption, parse_mode="HTML", reply_markup=markup)
    return {
        "ok": ok,
        "photo": bool(png),
        "pair": str(enriched.get("pair") or enriched.get("symbol") or ""),
        "chat_hint": _mask_chat(chat),
        "error": None if ok else (detail or "send_failed"),
    }
