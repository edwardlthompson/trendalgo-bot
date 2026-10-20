"""Device exchange-key vault (CredMan) + scope metadata (Phase 1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from trendalgo.device.wizard.credentials import (
    CredentialError,
    CredentialStore,
    MemoryCredentialStore,
    open_store,
)
from trendalgo.exchanges.secrets import EnvSecretStore, SecretStore

KeyScope = Literal["query", "trade"]
TARGET_PREFIX = "TrendAlgo/exchange/"


@dataclass(frozen=True)
class VaultEntry:
    exchange_id: str
    api_key: str
    api_secret: str
    scope: KeyScope
    verified_at: str | None = None


def _targets(exchange_id: str) -> tuple[str, str, str]:
    base = f"{TARGET_PREFIX}{exchange_id}"
    return f"{base}/key", f"{base}/secret", f"{base}/meta"


class VaultSecretStore:
    """SecretStore that prefers CredMan vault entries, then process env."""

    def __init__(
        self,
        store: CredentialStore | None = None,
        *,
        env: SecretStore | None = None,
    ) -> None:
        self._cred = store
        self._env = env or EnvSecretStore()
        self._env_names: dict[str, tuple[str, str]] = {}

    def bind_exchange(self, exchange_id: str, env_key: str, env_secret: str) -> None:
        self._env_names[env_key] = (exchange_id, "key")
        self._env_names[env_secret] = (exchange_id, "secret")

    def bind_registry(self) -> None:
        from trendalgo.exchanges.registry import load_registry

        for entry in load_registry().exchanges:
            self.bind_exchange(entry.id, entry.env_key, entry.env_secret)

    def _cred_store(self) -> CredentialStore | None:
        if self._cred is not None:
            return self._cred
        try:
            return open_store()
        except CredentialError:
            return None

    def get(self, name: str) -> str | None:
        binding = self._env_names.get(name)
        if binding is not None:
            exchange_id, which = binding
            entry = self.read_entry(exchange_id)
            if entry is not None:
                return entry.api_key if which == "key" else entry.api_secret
        return self._env.get(name)

    def read_entry(self, exchange_id: str) -> VaultEntry | None:
        vault = self._cred_store()
        if vault is None:
            return None
        key_t, secret_t, meta_t = _targets(exchange_id)
        try:
            api_key = vault.read(key_t)
            api_secret = vault.read(secret_t)
            meta_raw = vault.read(meta_t) or "{}"
        except CredentialError:
            return None
        if not api_key or not api_secret:
            return None
        try:
            meta = json.loads(meta_raw)
        except json.JSONDecodeError:
            meta = {}
        scope = meta.get("scope", "query")
        if scope not in ("query", "trade"):
            scope = "query"
        return VaultEntry(
            exchange_id=exchange_id,
            api_key=api_key,
            api_secret=api_secret,
            scope=scope,  # type: ignore[arg-type]
            verified_at=meta.get("verified_at"),
        )

    def write_entry(self, entry: VaultEntry) -> None:
        vault = self._cred_store()
        if vault is None:
            raise CredentialError("No credential vault available on this platform.")
        key_t, secret_t, meta_t = _targets(entry.exchange_id)
        vault.write(key_t, entry.api_key)
        vault.write(secret_t, entry.api_secret)
        vault.write(
            meta_t,
            json.dumps({"scope": entry.scope, "verified_at": entry.verified_at}),
        )

    def delete_entry(self, exchange_id: str) -> None:
        vault = self._cred_store()
        if vault is None:
            return
        for target in _targets(exchange_id):
            try:
                vault.delete(target)
            except CredentialError:
                pass

    def can_place_orders(self, exchange_id: str) -> bool:
        entry = self.read_entry(exchange_id)
        return entry is not None and entry.scope == "trade"


def memory_vault_for_tests() -> tuple[VaultSecretStore, MemoryCredentialStore]:
    mem = MemoryCredentialStore()
    return VaultSecretStore(mem), mem
