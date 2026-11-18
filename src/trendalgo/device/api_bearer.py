"""Desktop bearer for the main API (AUTH-05). Keyring miss → re-pair, never open access."""

from __future__ import annotations

from dataclasses import dataclass

from trendalgo.device.wizard.credentials import (
    OWNER_BEARER_TARGET,
    CredentialError,
    CredentialStore,
    open_store,
)


@dataclass(frozen=True)
class BearerLoad:
    token: str | None
    must_repair: bool
    reason: str


def load_api_bearer(store: CredentialStore | None = None) -> BearerLoad:
    """Read the short-lived bearer. On vault failure, signal re-pair (not open access)."""
    vault = store if store is not None else open_store()
    try:
        token = vault.read(OWNER_BEARER_TARGET)
    except CredentialError as exc:
        return BearerLoad(token=None, must_repair=True, reason=str(exc))
    if not token:
        return BearerLoad(token=None, must_repair=True, reason="bearer_missing")
    return BearerLoad(token=token, must_repair=False, reason="ok")


def save_api_bearer(token: str, store: CredentialStore | None = None) -> BearerLoad:
    vault = store if store is not None else open_store()
    try:
        vault.write(OWNER_BEARER_TARGET, token)
    except CredentialError as exc:
        return BearerLoad(token=None, must_repair=True, reason=str(exc))
    return BearerLoad(token=token, must_repair=False, reason="ok")


def clear_api_bearer(store: CredentialStore | None = None) -> None:
    vault = store if store is not None else open_store()
    try:
        vault.delete(OWNER_BEARER_TARGET)
    except CredentialError:
        pass
