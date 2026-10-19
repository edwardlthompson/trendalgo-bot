"""Gate alert events by NotifyPrefs for OS toast / Alerts tab / Telegram."""

from __future__ import annotations

from dataclasses import dataclass

from trendalgo.device.notify_prefs import NotifyPrefs
from trendalgo.device.scanner_alert_diff import AlertEvent


@dataclass(frozen=True)
class DispatchPlan:
    events: list[AlertEvent]
    toast: bool
    telegram: bool


def plan_for_event(event: AlertEvent, prefs: NotifyPrefs) -> DispatchPlan | None:
    kind = event.kind
    if kind == "qualified_enter":
        toast = prefs.windows_entered
        tg = prefs.telegram_enabled and prefs.telegram_entered
    elif kind == "watchlist_leave":
        toast = prefs.windows_left
        tg = prefs.telegram_enabled and prefs.telegram_left
    elif kind in {"scan_log", "backtest_log"}:
        toast = prefs.windows_logs
        tg = prefs.telegram_enabled and prefs.telegram_logs
    elif kind == "trade_alert":
        toast = prefs.windows_trades
        tg = prefs.telegram_enabled and prefs.telegram_trades
    else:
        return None
    if not toast and not tg:
        # Still allow history append upstream; dispatch only for notify channels.
        return None
    return DispatchPlan(events=[event], toast=toast, telegram=tg)


def plans_for(events: list[AlertEvent], prefs: NotifyPrefs) -> list[DispatchPlan]:
    out: list[DispatchPlan] = []
    for event in events:
        plan = plan_for_event(event, prefs)
        if plan is not None:
            out.append(plan)
    return out


def trade_telegram_enabled(prefs: NotifyPrefs) -> bool:
    return bool(prefs.telegram_enabled and prefs.telegram_trades)
