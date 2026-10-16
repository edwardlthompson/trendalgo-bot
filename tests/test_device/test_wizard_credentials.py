"""Secrets live in the vault, not in files. The Windows vault test runs only on Windows."""

from __future__ import annotations

import sys
import uuid
from types import SimpleNamespace

import pytest

from trendalgo.device.wizard import credentials
from trendalgo.device.wizard.credentials import (
    OWNER_SECRET_TARGET,
    PRACTICE_SECRET_TARGET,
    SECRET_BYTES,
    CredentialError,
    MemoryCredentialStore,
    WindowsCredentialStore,
    get_or_create_secret,
    open_store,
)


def test_a_memory_store_reads_writes_and_deletes() -> None:
    store = MemoryCredentialStore()
    assert store.read("a") is None
    store.write("a", "one")
    assert store.read("a") == "one"
    store.write("a", "two")
    assert store.read("a") == "two"
    store.delete("a")
    assert store.read("a") is None
    store.delete("a")


def test_a_missing_secret_is_created_once_and_then_reused() -> None:
    store = MemoryCredentialStore()
    first = get_or_create_secret(store, PRACTICE_SECRET_TARGET)
    second = get_or_create_secret(store, PRACTICE_SECRET_TARGET)
    assert first == second
    assert len(first) >= SECRET_BYTES
    assert store.read(PRACTICE_SECRET_TARGET) == first


def test_an_empty_stored_secret_is_replaced_not_reused() -> None:
    store = MemoryCredentialStore()
    store.write(PRACTICE_SECRET_TARGET, "")
    fresh = get_or_create_secret(store, PRACTICE_SECRET_TARGET)
    assert fresh != ""


def test_the_owner_and_practice_secrets_use_separate_targets() -> None:
    assert OWNER_SECRET_TARGET != PRACTICE_SECRET_TARGET
    store = MemoryCredentialStore()
    practice = get_or_create_secret(store, PRACTICE_SECRET_TARGET)
    store.write(OWNER_SECRET_TARGET, "owner-value")
    assert store.read(PRACTICE_SECRET_TARGET) == practice


def test_the_vault_is_refused_where_windows_is_not_the_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(credentials, "sys", SimpleNamespace(platform="linux"))
    with pytest.raises(CredentialError, match="only available on Windows"):
        open_store()


def _vault_refusing_every_call() -> WindowsCredentialStore:
    """A store whose vault calls all report failure. __init__ is skipped: it needs Windows."""
    store = object.__new__(WindowsCredentialStore)
    store._lib = SimpleNamespace(
        CredReadW=lambda *args: 0,
        CredWriteW=lambda *args: 0,
        CredDeleteW=lambda *args: 0,
        CredFree=lambda *args: None,
    )
    return store


def test_a_refused_write_names_the_windows_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credentials, "_last_error", lambda: 5)
    with pytest.raises(CredentialError, match=r"could not save it \(Windows error 5\)"):
        _vault_refusing_every_call().write("TrendAlgo/x", "value")


def test_a_refused_read_that_is_not_not_found_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credentials, "_last_error", lambda: 5)
    with pytest.raises(CredentialError, match=r"could not read it \(Windows error 5\)"):
        _vault_refusing_every_call().read("TrendAlgo/x")


def test_a_read_of_a_missing_entry_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credentials, "_last_error", lambda: 1168)
    assert _vault_refusing_every_call().read("TrendAlgo/x") is None


def test_a_refused_delete_that_is_not_not_found_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credentials, "_last_error", lambda: 5)
    with pytest.raises(CredentialError, match=r"could not delete it \(Windows error 5\)"):
        _vault_refusing_every_call().delete("TrendAlgo/x")


def test_deleting_a_missing_entry_is_harmless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credentials, "_last_error", lambda: 1168)
    _vault_refusing_every_call().delete("TrendAlgo/x")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Credential Manager only")
def test_the_windows_vault_round_trips_a_unique_test_entry() -> None:
    store = open_store()
    target = f"TrendAlgo/test-{uuid.uuid4().hex}"
    try:
        assert store.read(target) is None
        store.write(target, "first-value")
        assert store.read(target) == "first-value"
        store.write(target, "second-value")
        assert store.read(target) == "second-value"
    finally:
        store.delete(target)
    assert store.read(target) is None
    store.delete(target)
