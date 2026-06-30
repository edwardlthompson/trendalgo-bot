"""SMTP notifier tests."""

from __future__ import annotations

from typing import Any

import pytest

from trendalgo.notifications import email


def test_smtp_disabled_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_TO", raising=False)
    assert email.smtp_enabled() is False
    assert email.send_smtp_email("hi", "body")["sent"] is False


def test_smtp_enabled_with_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_TO", "user@example.com")
    assert email.smtp_enabled() is True


def test_send_smtp_email_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_TO", "user@example.com")
    monkeypatch.setenv("SMTP_USER", "bot")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    sent: list[Any] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int = 15) -> None:
            self.host = host
            self.port = port

        def __enter__(self) -> FakeSMTP:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def starttls(self) -> None:
            return None

        def login(self, user: str, password: str) -> None:
            sent.append(("login", user, password))

        def send_message(self, msg: object) -> None:
            sent.append(("message", msg))

    monkeypatch.setattr(email.smtplib, "SMTP", FakeSMTP)
    result = email.send_smtp_email("Subject", "Hello")
    assert result == {"sent": True}
    assert sent[0][0] == "login"


def test_send_smtp_email_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_TO", "user@example.com")

    class BrokenSMTP:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> BrokenSMTP:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def starttls(self) -> None:
            raise OSError("tls failed")

    monkeypatch.setattr(email.smtplib, "SMTP", BrokenSMTP)
    result = email.send_smtp_email("Subject", "Hello")
    assert result["sent"] is False
    assert "tls failed" in result["reason"]
