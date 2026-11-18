"""Alpaca CredMgr vault + resolve preference."""

from __future__ import annotations

import os

from trendalgo.device.alpaca_vault import (
    clear_alpaca_creds,
    has_alpaca_credentials,
    load_alpaca_creds,
    memory_store_for_tests,
    resolve_alpaca_credentials,
    save_alpaca_creds,
)
from trendalgo.device.alpaca_verify import verify_alpaca_keys


def test_vault_round_trip() -> None:
    store = memory_store_for_tests()
    save_alpaca_creds("PKTEST", "SECRET", store=store)
    assert load_alpaca_creds(store) == ("PKTEST", "SECRET")
    assert has_alpaca_credentials(store) is True
    clear_alpaca_creds(store=store)
    assert load_alpaca_creds(store) == (None, None)


def test_resolve_prefers_vault_over_env(monkeypatch: object) -> None:
    store = memory_store_for_tests()
    save_alpaca_creds("VAULT_KEY", "VAULT_SECRET", store=store)
    monkeypatch.setenv("ALPACA_API_KEY", "ENV_KEY")  # type: ignore[attr-defined]
    monkeypatch.setenv("ALPACA_API_SECRET", "ENV_SECRET")  # type: ignore[attr-defined]
    assert resolve_alpaca_credentials(store) == ("VAULT_KEY", "VAULT_SECRET")


def test_resolve_falls_back_to_env(monkeypatch: object) -> None:
    store = memory_store_for_tests()
    monkeypatch.setenv("ALPACA_API_KEY", "ENV_KEY")  # type: ignore[attr-defined]
    monkeypatch.setenv("ALPACA_API_SECRET", "ENV_SECRET")  # type: ignore[attr-defined]
    for key in ("ALPACA_API_KEY", "ALPACA_API_SECRET"):
        assert os.environ.get(key)
    assert resolve_alpaca_credentials(store) == ("ENV_KEY", "ENV_SECRET")


def test_verify_requires_both_keys() -> None:
    ok, msg = verify_alpaca_keys("", "x")
    assert ok is False
    assert "required" in msg.lower()
