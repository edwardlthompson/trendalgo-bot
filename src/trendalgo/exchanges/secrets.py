"""API keys: where they come from, and how they stay out of logs (E6).

Callers read keys through a SecretStore. The local device reads the process environment
(EnvSecretStore). The host's encrypted store replaces it in sprint p3 without changing callers.
SecretRedactor masks watched values and obvious key shapes in log records.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable
from typing import Protocol

MIN_SECRET_LENGTH = 8  # shorter values match too much ordinary text to mask safely
MASK = "***"

_PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")
_HEX_KEY = re.compile(r"\b0x[a-fA-F0-9]{64}\b")

_EXTRA_ENV_NAMES = (
    "DEX_SIGNER_KEY",
    "TRENDALGO_OWNER_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_WEBHOOK_SECRET",
    "TRADINGVIEW_WEBHOOK_SECRET",
    "GROKBOT_WEBHOOK_KEY",
    "CMC_API_KEY",
)


class SecretStore(Protocol):
    def get(self, name: str) -> str | None: ...


class EnvSecretStore:
    """Reads secrets from the process environment. An empty value counts as missing."""

    def get(self, name: str) -> str | None:
        return os.environ.get(name) or None


def redact(text: str, secrets: Iterable[str]) -> str:
    """Replace each secret that appears in text with MASK, then mask PEM / 0x hex keys."""
    for secret in secrets:
        if len(secret) >= MIN_SECRET_LENGTH:
            text = text.replace(secret, MASK)
    text = _PEM.sub(MASK, text)
    return _HEX_KEY.sub(MASK, text)


class SecretRedactor(logging.Filter):
    """Masks watched secret values and key-shaped substrings in every record it passes."""

    def __init__(self, store: SecretStore) -> None:
        super().__init__()
        self._store = store
        self._names: set[str] = set()
        self._extra: set[str] = set()

    def set_store(self, store: SecretStore) -> None:
        self._store = store

    def watch(self, *names: str) -> None:
        self._names.update(name for name in names if name)

    def watch_values(self, *plaintext: str) -> None:
        self._extra.update(v for v in plaintext if v and len(v) >= MIN_SECRET_LENGTH)

    def values(self) -> list[str]:
        found = (self._store.get(name) for name in sorted(self._names))
        from_store = [value for value in found if value]
        return sorted(set(from_store) | self._extra)

    def filter(self, record: logging.LogRecord) -> bool:
        values = self.values()
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = redact(record.exc_text, values)
        record.msg = redact(record.getMessage(), values)
        record.args = ()
        return True


_redactor: SecretRedactor | None = None


def protect_logs(*names: str, store: SecretStore | None = None) -> SecretRedactor:
    """Watch secret names and mask their values on every root log handler. Idempotent.

    Handlers added after the first call are not covered; call again after adding one.
    """
    global _redactor
    if _redactor is None:
        _redactor = SecretRedactor(store or EnvSecretStore())
        for handler in logging.getLogger().handlers:
            handler.addFilter(_redactor)
    elif store is not None:
        _redactor.set_store(store)
    _redactor.watch(*names)
    return _redactor


def protect_known_secrets(*, store: SecretStore | None = None) -> SecretRedactor:
    """Watch registry exchange env names plus DEX/owner/telegram/webhook keys."""
    names: list[str] = list(_EXTRA_ENV_NAMES)
    try:
        from trendalgo.exchanges.registry import list_exchanges

        for entry in list_exchanges():
            names.append(entry.env_key)
            names.append(entry.env_secret)
    except Exception:
        pass
    redactor = protect_logs(*names, store=store)
    source = store or EnvSecretStore()
    for name in names:
        value = source.get(name)
        if value:
            redactor.watch_values(value)
    return redactor
