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
from trendalgo.notifications.grokbot import telegram_ai_note
from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.notifications.telegram_alert_enrich import enrich_enter_coin
from trendalgo.notifications.telegram_chart import enter_alert_png, exit_alert_png
from trendalgo.notifications.telegram_format import format_qualified_enter, format_watchlist_leave
from trendalgo.notifications.telegram_keyboard import reply_markup_json


def process_scan_alerts(
    root: Path,
    *,
    coins: list[dict[str, Any]],
    watchlist_pairs: list[str],
    telegram: TelegramCommands | None = None,
    floors: dict[str, float] | None = None,
    board_coins: list[dict[str, Any]] | None = None,
    lane: str = "crypto",
) -> tuple[list[AlertEvent], list[dict[str, Any]]]:
    """Diff vs last filtered set; Telegram for new enters and filtered leaves.

    Cold seed: empty previous + non-empty current persists state with no events
    so a first run never spams every coin on the board.
    """
    previous = load_previous_qualified(root, lane=lane)
    keys = coin_keys(coins)
    if not previous and keys:
        save_previous_qualified(root, keys, coins=coins, lane=lane)
        return [], load_history(root)
    prev_coins = load_previous_coins(root, lane=lane)
    watch = watchlist_keys(watchlist_pairs)
    events = diff_alerts(
        previous=previous,
        current_coins=coins,
        watchlist=watch,
        previous_coins=prev_coins,
        board_coins=board_coins,
        floors=floors,
    )
    history = append_alerts(root, events) if events else load_history(root)
    save_previous_qualified(root, keys, coins=coins, lane=lane)
    prefs = load_prefs(root)
    for plan in plans_for(events, prefs):
        for event in plan.events:
            if plan.telegram:
                _send_telegram(event, client=telegram)
    for event in events:
        _emit_grokbot(event)
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


def _why_markup(event: AlertEvent, existing: str) -> str:
    from trendalgo.notifications.grokbot_explain import why_markup
    from trendalgo.notifications.grokbot_payload import coin_payload, envelope

    kind = "qualified_enter" if event.kind == "qualified_enter" else "qualified_leave"
    if isinstance(event.coin, dict):
        return why_markup(coin_payload(kind, event.coin, reason=event.reason), existing)
    return why_markup(envelope(event_type=kind, pair=event.pair, reason=event.reason), existing)


def _emit_grokbot(event: AlertEvent) -> None:
    from trendalgo.notifications.grokbot import emit
    from trendalgo.notifications.grokbot_payload import coin_payload, envelope

    kind = "qualified_enter" if event.kind == "qualified_enter" else "qualified_leave"
    if event.kind not in {"qualified_enter", "watchlist_leave"}:
        return
    if isinstance(event.coin, dict):
        emit(coin_payload(kind, event.coin, reason=event.reason))
        return
    emit(envelope(event_type=kind, pair=event.pair, reason=event.reason))


def _send_telegram(event: AlertEvent, *, client: TelegramCommands | None) -> None:
    tg = client
    if tg is None:
        token, chat = load_telegram_creds()
        tg = TelegramCommands(token=token, chat_id=chat)
    if not tg.enabled:
        return
    if event.kind == "qualified_enter" and event.coin is not None:
        coin = enrich_enter_coin(event.coin)
        caption = telegram_ai_note(format_qualified_enter(coin))
        markup = _why_markup(event, reply_markup_json(coin))
        png = enter_alert_png(coin)
        if png:
            tg.send_photo(png, caption, parse_mode="HTML", reply_markup=markup)
        else:
            tg.send_message(caption, parse_mode="HTML", reply_markup=markup)
        return
    if event.kind == "watchlist_leave":
        raw = event.coin if isinstance(event.coin, dict) else {"symbol": event.symbol}
        coin = (
            enrich_enter_coin(raw)
            if raw.get("ohlc_1h") or raw.get("backtest_top_strategies")
            else raw
        )
        caption = telegram_ai_note(
            format_watchlist_leave(symbol=event.symbol, reason=event.reason, coin=coin)
        )
        markup = _why_markup(event, reply_markup_json(coin))
        png = exit_alert_png(coin)
        if png:
            tg.send_photo(png, caption, parse_mode="HTML", reply_markup=markup)
        else:
            tg.send_message(caption, parse_mode="HTML", reply_markup=markup)
