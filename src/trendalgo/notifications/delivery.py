"""Preference-aware notification fan-out."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from trendalgo.notifications.preferences import load_preferences
from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.portfolio.db import PortfolioStore


class MessageChannel(Protocol):
    enabled: bool

    def send_message(self, text: str) -> bool: ...


class AlertDelivery:
    """Deliver alerts to independent inbox and Telegram channels."""

    def __init__(
        self,
        store: PortfolioStore,
        telegram: MessageChannel | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.store = store
        self.telegram = telegram or TelegramCommands()
        self.on_log = on_log

    def deliver(
        self,
        category: str,
        title: str,
        body: str,
        *,
        preference: str = "scanner",
    ) -> int | None:
        try:
            prefs = load_preferences(self.store)
        except Exception as exc:
            self._log(f"notification preferences failed: {exc}")
            return None
        if not bool(getattr(prefs, preference, False)):
            return None

        inbox_id: int | None = None
        errors: list[str] = []
        try:
            inbox_id = self.store.insert_notification(category, title, body)
        except Exception as exc:
            errors.append(f"inbox: {exc}")

        if prefs.push_enabled and self.telegram.enabled:
            try:
                if not self.telegram.send_message(f"{title}\n{body}"):
                    errors.append("telegram: delivery failed")
            except Exception as exc:
                errors.append(f"telegram: {exc}")

        if errors:
            message = "; ".join(errors)
            self._log(f"notification delivery error: {message}")
            if inbox_id is not None:
                try:
                    self.store.set_notification_delivery_error(inbox_id, message)
                except Exception as exc:
                    self._log(f"notification error recording failed: {exc}")
        return inbox_id

    def _log(self, message: str) -> None:
        if self.on_log:
            self.on_log(message)
