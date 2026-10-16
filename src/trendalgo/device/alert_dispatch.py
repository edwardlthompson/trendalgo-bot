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
    if event.kind == "qualified_enter":
        if not prefs.qualified_alerts:
            return None
        return DispatchPlan(
            events=[event],
            toast=True,
            telegram=prefs.telegram_enabled and prefs.telegram_qualified,
        )
    if event.kind == "watchlist_leave":
        if not prefs.watchlist_alerts:
            return None
        return DispatchPlan(
            events=[event],
            toast=True,
            telegram=prefs.telegram_enabled and prefs.telegram_watchlist,
        )
    return None


def plans_for(events: list[AlertEvent], prefs: NotifyPrefs) -> list[DispatchPlan]:
    out: list[DispatchPlan] = []
    for event in events:
        plan = plan_for_event(event, prefs)
        if plan is not None:
            out.append(plan)
    return out


def trade_telegram_enabled(prefs: NotifyPrefs) -> bool:
    return prefs.trade_alerts and prefs.telegram_enabled and prefs.telegram_trades
