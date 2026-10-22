"""After a successful scan: diff, persist history, optional Telegram photo/text."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.alert_dispatch import plans_for
from trendalgo.device.notify_prefs import load_prefs
from trendalgo.device.scanner_alert_diff import AlertEvent, coin_keys, diff_alerts, watchlist_keys
from trendalgo.device.scanner_alerts_store import (
    append_alerts,
    load_history,
    load_previous_coins,
    load_previous_qualified,
    save_previous_qualified,
)
from trendalgo.device.telegram_vault import load_telegram_creds
from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.notifications.telegram_chart import chart_png_bytes, closes_from_coin
from trendalgo.notifications.telegram_format import format_qualified_enter, format_watchlist_leave


def process_scan_alerts(
    root: Path,
    *,
    coins: list[dict[str, Any]],
    watchlist_pairs: list[str],
    telegram: TelegramCommands | None = None,
    floors: dict[str, float] | None = None,
) -> tuple[list[AlertEvent], list[dict[str, Any]]]:
    """Diff vs last qualified set, append history, send Telegram when prefs allow."""
    previous = load_previous_qualified(root)
    prev_coins = load_previous_coins(root)
    watch = watchlist_keys(watchlist_pairs)
    events = diff_alerts(
        previous=previous,
        current_coins=coins,
        watchlist=watch,
        previous_coins=prev_coins,
        floors=floors,
    )
    history = append_alerts(root, events) if events else load_history(root)
    save_previous_qualified(root, coin_keys(coins), coins=coins)
    prefs = load_prefs(root)
    for plan in plans_for(events, prefs):
        for event in plan.events:
            if plan.telegram:
                _send_telegram(event, client=telegram)
    return events, history


def toast_lines(events: list[AlertEvent], prefs_root: Path) -> list[tuple[str, str]]:
    from trendalgo.device.alert_preview import windows_preview

    prefs = load_prefs(prefs_root)
    lines: list[tuple[str, str]] = []
    for plan in plans_for(events, prefs):
        if not plan.toast:
            continue
        for event in plan.events:
            lines.append(windows_preview(event))
    return lines


def _send_telegram(event: AlertEvent, *, client: TelegramCommands | None) -> None:
    tg = client
    if tg is None:
        token, chat = load_telegram_creds()
        tg = TelegramCommands(token=token, chat_id=chat)
    if not tg.enabled:
        return
    if event.kind == "qualified_enter" and event.coin is not None:
        caption = format_qualified_enter(event.coin)
        png = chart_png_bytes(closes_from_coin(event.coin), title=event.symbol)
        if png:
            tg.send_photo(png, caption)
        else:
            tg.send_message(caption)
        return
    if event.kind == "watchlist_leave":
        tg.send_message(format_watchlist_leave(symbol=event.symbol, reason=event.reason))
