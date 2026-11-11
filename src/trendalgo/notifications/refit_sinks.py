"""Concrete re-fit notification sinks (NOTIF-01)."""

from __future__ import annotations

from trendalgo.notifications.discord import discord_enabled, send_discord_message
from trendalgo.notifications.email import send_smtp_email, smtp_enabled
from trendalgo.notifications.ntfy import ntfy_enabled, send_ntfy
from trendalgo.notifications.refit_pipeline import SinkResult
from trendalgo.notifications.telegram import TelegramCommands


class NtfySink:
    name = "ntfy"

    def send(self, title: str, body: str) -> SinkResult:
        if not ntfy_enabled():
            return SinkResult(ok=False, detail="ntfy disabled", sink=self.name)
        result = send_ntfy(title, body)
        return SinkResult(ok=bool(result.get("sent")), detail=str(result), sink=self.name)


class TelegramSink:
    name = "telegram"

    def __init__(self, client: TelegramCommands | None = None) -> None:
        self._client = client or TelegramCommands()

    def send(self, title: str, body: str) -> SinkResult:
        if not self._client.enabled:
            return SinkResult(ok=False, detail="telegram disabled", sink=self.name)
        ok = bool(self._client.send_message(f"{title}\n{body}"))
        return SinkResult(ok=ok, detail="sent" if ok else "failed", sink=self.name)


class DiscordSink:
    name = "discord"

    def send(self, title: str, body: str) -> SinkResult:
        if not discord_enabled():
            return SinkResult(ok=False, detail="discord disabled", sink=self.name)
        result = send_discord_message(f"{title}\n{body}")
        return SinkResult(ok=bool(result.get("sent")), detail=str(result), sink=self.name)


class EmailSink:
    name = "email"

    def send(self, title: str, body: str) -> SinkResult:
        if not smtp_enabled():
            return SinkResult(ok=False, detail="smtp disabled", sink=self.name)
        result = send_smtp_email(title, body)
        return SinkResult(ok=bool(result.get("sent")), detail=str(result), sink=self.name)


def default_sinks() -> list[NtfySink | TelegramSink | DiscordSink | EmailSink]:
    return [NtfySink(), TelegramSink(), DiscordSink(), EmailSink()]
