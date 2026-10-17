"""Credential Manager targets for calendar API keys."""

from __future__ import annotations

from trendalgo.device.wizard.credentials import CredentialStore, open_store

CMC_TARGET = "TrendAlgo/calendar-coinmarketcal"
COINDAR_TARGET = "TrendAlgo/calendar-coindar"


def read_cmc_key(store: CredentialStore | None = None) -> str | None:
    return (store or open_store()).read(CMC_TARGET)


def write_cmc_key(secret: str, store: CredentialStore | None = None) -> None:
    (store or open_store()).write(CMC_TARGET, secret.strip())


def read_coindar_token(store: CredentialStore | None = None) -> str | None:
    return (store or open_store()).read(COINDAR_TARGET)


def write_coindar_token(secret: str, store: CredentialStore | None = None) -> None:
    (store or open_store()).write(COINDAR_TARGET, secret.strip())


def any_key_present(store: CredentialStore | None = None) -> bool:
    try:
        vault = store or open_store()
    except Exception:
        return False
    try:
        return bool(vault.read(CMC_TARGET) or vault.read(COINDAR_TARGET))
    except Exception:
        return False
