"""Alpaca API key id + secret in Windows Credential Manager (device vault)."""

from __future__ import annotations

import os

from trendalgo.brokers.registry import load_broker_registry
from trendalgo.device.wizard.credentials import (
    CredentialError,
    CredentialStore,
    MemoryCredentialStore,
    open_store,
)

ALPACA_KEY_TARGET = "TrendAlgo/alpaca-key-id"
ALPACA_SECRET_TARGET = "TrendAlgo/alpaca-secret"


def load_alpaca_creds(
    store: CredentialStore | None = None,
) -> tuple[str | None, str | None]:
    vault = store or _safe_store()
    if vault is None:
        return None, None
    try:
        return vault.read(ALPACA_KEY_TARGET), vault.read(ALPACA_SECRET_TARGET)
    except CredentialError:
        return None, None


def save_alpaca_creds(
    key_id: str,
    secret: str,
    store: CredentialStore | None = None,
) -> None:
    vault = store or open_store()
    vault.write(ALPACA_KEY_TARGET, key_id.strip())
    vault.write(ALPACA_SECRET_TARGET, secret.strip())


def clear_alpaca_creds(store: CredentialStore | None = None) -> None:
    vault = store or open_store()
    vault.delete(ALPACA_KEY_TARGET)
    vault.delete(ALPACA_SECRET_TARGET)


def resolve_alpaca_credentials(
    store: CredentialStore | None = None,
) -> tuple[str, str] | None:
    """Prefer Credential Manager vault, then registry env vars."""
    key, secret = load_alpaca_creds(store)
    if key and secret:
        return key.strip(), secret.strip()
    entry = load_broker_registry().by_id("alpaca")
    if entry is None:
        return None
    env_key = os.environ.get(entry.env_key, "").strip()
    env_secret = os.environ.get(entry.env_secret, "").strip()
    if not env_key or not env_secret:
        return None
    return env_key, env_secret


def has_alpaca_credentials(store: CredentialStore | None = None) -> bool:
    return resolve_alpaca_credentials(store) is not None


def _safe_store() -> CredentialStore | None:
    try:
        return open_store()
    except CredentialError:
        return None


def memory_store_for_tests() -> MemoryCredentialStore:
    return MemoryCredentialStore()
