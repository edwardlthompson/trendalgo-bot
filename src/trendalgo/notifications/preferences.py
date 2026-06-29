"""Notification preference models."""

from __future__ import annotations

from pydantic import BaseModel

from trendalgo.portfolio.db import PortfolioStore


class NotificationPreferences(BaseModel):
    trades: bool = True
    pnl_swings: bool = True
    fees: bool = True
    scanner: bool = False
    push_enabled: bool = False
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None

    model_config = {"extra": "forbid"}


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def load_preferences(store: PortfolioStore) -> NotificationPreferences:
    row = store.get_notification_preferences()
    if not row:
        return NotificationPreferences()
    return NotificationPreferences(
        trades=bool(row.get("trades")),
        pnl_swings=bool(row.get("pnl_swings")),
        fees=bool(row.get("fees")),
        scanner=bool(row.get("scanner")),
        push_enabled=bool(row.get("push_enabled")),
        quiet_hours_start=_optional_str(row.get("quiet_hours_start")),
        quiet_hours_end=_optional_str(row.get("quiet_hours_end")),
    )


def save_preferences(
    store: PortfolioStore, prefs: NotificationPreferences
) -> NotificationPreferences:
    store.update_notification_preferences(prefs.model_dump())
    return prefs
