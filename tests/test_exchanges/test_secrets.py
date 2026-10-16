"""Keys come from a SecretStore and never reach a log line (E6)."""

from __future__ import annotations

import logging

import pytest

from trendalgo.exchanges import secrets
from trendalgo.exchanges.registry import get_entry
from trendalgo.exchanges.secrets import EnvSecretStore, SecretRedactor, protect_logs, redact

SECRET = "s3cr3t-value-123"


class MapStore:
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def get(self, name: str) -> str | None:
        return self._values.get(name)


class Collect(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


def test_env_store_reads_the_environment_and_treats_empty_as_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TA_TEST_KEY", raising=False)
    assert EnvSecretStore().get("TA_TEST_KEY") is None
    monkeypatch.setenv("TA_TEST_KEY", "")
    assert EnvSecretStore().get("TA_TEST_KEY") is None
    monkeypatch.setenv("TA_TEST_KEY", "abcd1234efgh")
    assert EnvSecretStore().get("TA_TEST_KEY") == "abcd1234efgh"


def test_redact_masks_long_secrets_and_leaves_short_ones_alone() -> None:
    assert redact("key=abcd1234efgh", ["abcd1234efgh"]) == "key=***"
    assert redact("pin=1234", ["1234"]) == "pin=1234"  # too short to mask safely


def test_has_api_keys_asks_the_store_not_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = get_entry("kraken")
    monkeypatch.setenv(entry.env_key, "k1")
    monkeypatch.setenv(entry.env_secret, "s1")
    assert not entry.has_api_keys(MapStore({}))
    assert entry.has_api_keys(MapStore({entry.env_key: "k", entry.env_secret: "s"}))
    assert not entry.has_api_keys(MapStore({entry.env_key: "k"}))


def test_no_log_line_carries_a_watched_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TA_TEST_SECRET", SECRET)
    redactor = SecretRedactor(EnvSecretStore())
    redactor.watch("TA_TEST_SECRET")
    handler = Collect()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(redactor)
    log = logging.getLogger("trendalgo.test.redaction")
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    try:
        log.info("login with %s failed", SECRET)
        try:
            raise ValueError(f"bad key {SECRET}")
        except ValueError:
            log.exception("request failed")
    finally:
        log.removeHandler(handler)
    assert handler.lines[0] == "login with *** failed"
    assert SECRET not in "\n".join(handler.lines)
    assert "ValueError: bad key ***" in handler.lines[1]


def test_protect_logs_keeps_one_shared_redactor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(secrets, "_redactor", None)
    monkeypatch.setenv("TA_TEST_PROTECT", "abcdefgh1234")
    first = protect_logs("TA_TEST_PROTECT")
    second = protect_logs("TA_TEST_PROTECT")
    assert first is second
    assert "abcdefgh1234" in first.values()
