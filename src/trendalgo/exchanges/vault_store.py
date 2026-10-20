"""Re-export device vault SecretStore for exchange adapters (Phase 1)."""

from __future__ import annotations

from trendalgo.device.secrets_vault import (
    VaultEntry,
    VaultSecretStore,
    memory_vault_for_tests,
)

__all__ = ["VaultEntry", "VaultSecretStore", "memory_vault_for_tests"]
