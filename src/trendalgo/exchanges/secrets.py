"""API keys: where they come from, and how they stay out of logs (E6).

Callers read keys through a SecretStore. The local device reads the process environment
(EnvSecretStore). The host's encrypted store replaces it in sprint p3 without changing callers.
SecretRedactor masks the value of every watched key in log records, so a key never reaches a log.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from typing import Protocol

MIN_SECRET_LENGTH = 8  # shorter values match too much ordinary text to mask safely
MASK = "***"


class SecretStore(Protocol):
    def get(self, name: str) -> str | None: ...


class EnvSecretStore:
    """Reads secrets from the process environment. An empty value counts as missing."""

    def get(self, name: str) -> str | None:
        return os.environ.get(name) or None


def redact(text: str, secrets: Iterable[str]) -> str:
    """Replace each secret that appears in text with MASK."""
    for secret in secrets:
        if len(secret) >= MIN_SECRET_LENGTH:
            text = text.replace(secret, MASK)
    return text


class SecretRedactor(logging.Filter):
    """Masks the values of watched secret names in every record it passes."""

    def __init__(self, store: SecretStore) -> None:
        super().__init__()
        self._store = store
        self._names: set[str] = set()

    def watch(self, *names: str) -> None:
        self._names.update(name for name in names if name)

    def values(self) -> list[str]:
        found = (self._store.get(name) for name in sorted(self._names))
        return [value for value in found if value]

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


def protect_logs(*names: str) -> SecretRedactor:
    """Watch secret env names and mask their values on every root log handler. Idempotent.

    Handlers added after the first call are not covered; call again after adding one.
    """
    global _redactor
    if _redactor is None:
        _redactor = SecretRedactor(EnvSecretStore())
        for handler in logging.getLogger().handlers:
            handler.addFilter(_redactor)
    _redactor.watch(*names)
    return _redactor
