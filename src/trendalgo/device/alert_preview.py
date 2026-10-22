"""Sample alerts + Windows/Telegram preview text + master kind prefs for the Alerts ribbon."""

from __future__ import annotations

from dataclasses import replace

from trendalgo.device import strings as S
from trendalgo.device.notify_prefs import NotifyPrefs
from trendalgo.device.scanner_alert_diff import AlertEvent
from trendalgo.notifications.telegram_format import (
    format_qualified_enter,
    format_trade,
    format_watchlist_leave,
)

KINDS = ("entered", "left", "trades")
SAMPLE_SYMBOL = "BTC"
SAMPLE_PAIR = "BTC/USD"

_EVENT_KIND = {
    "entered": "qualified_enter",
    "left": "watchlist_leave",
    "trades": "trade_alert",
}


def sample_event(kind: str) -> AlertEvent:
    """Realistic sample used for preview and Test buttons."""
    if kind == "entered":
        coin = {
            "symbol": SAMPLE_SYMBOL,
            "pair": SAMPLE_PAIR,
            "gain_7d": 12.5,
            "gain_30d": 28.0,
            "health": 0.82,
            "uniformity": 0.71,
            "volume_24h": 12_500_000,
            "listed_on": ["kraken", "coinbase"],
            "best_bt": "RSI(14) 1h",
            "strategies": [
                {"name": "RSI(14) 1h", "pnl_pct": 18.2, "vs_bh": 4.1},
                {"name": "EMA cross 4h", "pnl_pct": 11.0, "vs_bh": 1.2},
            ],
            "closes_7d": [100 + i * 0.4 for i in range(48)],
        }
        return AlertEvent(
            kind="qualified_enter",
            symbol=SAMPLE_SYMBOL,
            pair=SAMPLE_PAIR,
            reason="Passed volume + uniformity gates",
            coin=coin,
        )
    if kind == "left":
        return AlertEvent(
            kind="watchlist_leave",
            symbol=SAMPLE_SYMBOL,
            pair=SAMPLE_PAIR,
            reason="Dropped below min gain / left qualified set",
        )
    if kind == "trades":
        return AlertEvent(
            kind="trade_alert",
            symbol=SAMPLE_SYMBOL,
            pair=SAMPLE_PAIR,
            reason="buy 0.01 @ 64000 fee=$1.20 pnl=$0.00",
        )
    raise ValueError(f"unknown alert kind: {kind}")


def windows_preview(event: AlertEvent) -> tuple[str, str]:
    """Title/body for OS toast — same shape as live scanner toasts."""
    if event.kind == "qualified_enter":
        return S.ALERT_ENTER_TITLE.format(symbol=event.symbol), event.reason
    if event.kind == "watchlist_leave":
        return S.ALERT_LEAVE_TITLE.format(symbol=event.symbol), event.reason
    if event.kind == "trade_alert":
        return S.ALERT_TRADE_TITLE.format(pair=event.pair), event.reason
    return event.kind, event.reason


def telegram_preview(event: AlertEvent) -> str:
    if event.kind == "qualified_enter" and event.coin is not None:
        return format_qualified_enter(event.coin)
    if event.kind == "watchlist_leave":
        return format_watchlist_leave(symbol=event.symbol, reason=event.reason)
    if event.kind == "trade_alert":
        return format_trade(
            pair=event.pair,
            side="buy",
            amount=0.01,
            price=64_000.0,
            fee_usd=1.2,
            realized_pnl_usd=0.0,
            plan_version=1,
        )
    return event.reason


def kind_master_on(prefs: NotifyPrefs, kind: str) -> bool:
    win, tg = _flags(prefs, kind)
    return bool(win and tg)


def set_kind_master(prefs: NotifyPrefs, kind: str, enabled: bool) -> NotifyPrefs:
    """Force both Windows and Telegram delivery flags for a ribbon kind."""
    if kind == "entered":
        return replace(prefs, windows_entered=enabled, telegram_entered=enabled)
    if kind == "left":
        return replace(prefs, windows_left=enabled, telegram_left=enabled)
    if kind == "trades":
        return replace(prefs, windows_trades=enabled, telegram_trades=enabled)
    raise ValueError(f"unknown alert kind: {kind}")


def event_kind_for(kind: str) -> str:
    return _EVENT_KIND[kind]


def _flags(prefs: NotifyPrefs, kind: str) -> tuple[bool, bool]:
    if kind == "entered":
        return prefs.windows_entered, prefs.telegram_entered
    if kind == "left":
        return prefs.windows_left, prefs.telegram_left
    if kind == "trades":
        return prefs.windows_trades, prefs.telegram_trades
    raise ValueError(f"unknown alert kind: {kind}")
