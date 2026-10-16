"""Telegram bot token + chat id in Windows Credential Manager (device vault)."""

from __future__ import annotations

from trendalgo.device.wizard.credentials import (
    CredentialError,
    CredentialStore,
    MemoryCredentialStore,
    open_store,
)

TELEGRAM_TOKEN_TARGET = "TrendAlgo/telegram-bot-token"
TELEGRAM_CHAT_TARGET = "TrendAlgo/telegram-chat-id"


def load_telegram_creds(
    store: CredentialStore | None = None,
) -> tuple[str | None, str | None]:
    vault = store or _safe_store()
    if vault is None:
        return None, None
    try:
        return vault.read(TELEGRAM_TOKEN_TARGET), vault.read(TELEGRAM_CHAT_TARGET)
    except CredentialError:
        return None, None


def save_telegram_creds(
    token: str,
    chat_id: str,
    store: CredentialStore | None = None,
) -> None:
    vault = store or open_store()
    vault.write(TELEGRAM_TOKEN_TARGET, token.strip())
    vault.write(TELEGRAM_CHAT_TARGET, chat_id.strip())


def clear_telegram_creds(store: CredentialStore | None = None) -> None:
    vault = store or open_store()
    vault.delete(TELEGRAM_TOKEN_TARGET)
    vault.delete(TELEGRAM_CHAT_TARGET)


def _safe_store() -> CredentialStore | None:
    try:
        return open_store()
    except CredentialError:
        return None


def memory_store_for_tests() -> MemoryCredentialStore:
    return MemoryCredentialStore()
