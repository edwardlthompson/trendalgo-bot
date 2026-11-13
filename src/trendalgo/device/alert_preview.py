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


def _sample_coin() -> dict[str, object]:
    closes = [100 + i * 0.4 for i in range(48)]
    return {
        "symbol": SAMPLE_SYMBOL,
        "name": "Bitcoin",
        "pair": SAMPLE_PAIR,
        "gains": {"7d": 12.5, "30d": 28.0},
        "health_score": 82.0,
        "uniformity_score": 71.0,
        "volume_24h": 12_500_000,
        "listed_on": ["kraken", "coinbase"],
        "exchange_volumes": {"kraken": 8_000_000, "coinbase": 4_500_000},
        "cmc_slug": "bitcoin",
        "current_rank": 1,
        "best_bt": "RSI(14) 1h",
        "strategies": [
            {
                "name": "RSI",
                "timeframe": "1h",
                "params": "lo=30; p=14",
                "net_pct": 18.2,
                "trades": 4,
                "win_pct": 75.0,
            },
            {
                "name": "EMA cross",
                "timeframe": "4h",
                "params": "fast=12; slow=26",
                "net_pct": 11.0,
                "trades": 3,
                "win_pct": 66.0,
            },
        ],
        "buy_hold": {"timeframe": "1h", "net_pct": 8.0},
        "spark_closes_7d": closes,
        "alert_trades": [
            {
                "entry_index": 8,
                "exit_index": 20,
                "entry_price": closes[8],
                "exit_price": closes[20],
                "pnl_pct": 5.2,
            },
            {
                "entry_index": 28,
                "exit_index": 40,
                "entry_price": closes[28],
                "exit_price": closes[40],
                "pnl_pct": 4.1,
            },
        ],
        "exit_reason": "7d gain below threshold",
        "lifecycle_pnl_pct": 6.4,
        "max_runup_pct": 14.0,
        "max_drawdown_pct": -3.2,
        "held_days": 5,
    }


def sample_event(kind: str) -> AlertEvent:
    """Realistic sample used for preview and Test buttons (LTS-shaped coin)."""
    if kind == "entered":
        return AlertEvent(
            kind="qualified_enter",
            symbol=SAMPLE_SYMBOL,
            pair=SAMPLE_PAIR,
            reason="Passed volume + uniformity gates",
            coin=_sample_coin(),
        )
    if kind == "left":
        return AlertEvent(
            kind="watchlist_leave",
            symbol=SAMPLE_SYMBOL,
            pair=SAMPLE_PAIR,
            reason="7d gain below threshold",
            coin=_sample_coin(),
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
        return format_watchlist_leave(symbol=event.symbol, reason=event.reason, coin=event.coin)
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
