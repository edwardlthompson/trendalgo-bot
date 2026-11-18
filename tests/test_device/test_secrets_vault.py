"""Encrypted vault + key verify (Phase 1 / 5)."""

from __future__ import annotations

import pytest

from trendalgo.device.secrets_vault import VaultEntry, VaultSecretStore, memory_vault_for_tests
from trendalgo.device.wizard.credentials import CredentialError, MemoryCredentialStore
from trendalgo.trading.key_verify import success_dialog_text, verify_exchange_keys


class _FailOnSecondWrite(MemoryCredentialStore):
    """Writes the first target, then refuses — exercises vault rollback."""

    def __init__(self) -> None:
        super().__init__()
        self._writes = 0

    def write(self, target: str, secret: str) -> None:
        self._writes += 1
        if self._writes >= 2:
            raise CredentialError("stub refused second write")
        super().write(target, secret)


def test_vault_round_trip_query_scope() -> None:
    store, _mem = memory_vault_for_tests()
    store.bind_exchange("kraken", "KRAKEN_API_KEY", "KRAKEN_API_SECRET")
    store.write_entry(
        VaultEntry(
            exchange_id="kraken",
            api_key="fixture",
            api_secret="fixture",
            scope="query",
        )
    )
    entry = store.read_entry("kraken")
    assert entry is not None
    assert entry.scope == "query"
    assert store.can_place_orders("kraken") is False
    assert store.get("KRAKEN_API_KEY") == "fixture"
    store.delete_entry("kraken")
    assert store.read_entry("kraken") is None


def test_trade_scope_can_place_orders() -> None:
    store, _ = memory_vault_for_tests()
    store.write_entry(
        VaultEntry(
            exchange_id="kraken",
            api_key="fixture",
            api_secret="fixture",
            scope="trade",
        )
    )
    assert store.can_place_orders("kraken") is True


def test_write_entry_rolls_back_partial_pair() -> None:
    mem = _FailOnSecondWrite()
    store = VaultSecretStore(mem)
    with pytest.raises(CredentialError, match="stub refused"):
        store.write_entry(
            VaultEntry(
                exchange_id="kraken",
                api_key="partial-key",
                api_secret="partial-secret",
                scope="query",
            )
        )
    assert store.read_entry("kraken") is None
    # First write target must not linger after rollback.
    assert mem.read("TrendAlgo/exchange/kraken/key") is None


def test_key_verify_allowlist_and_dialog() -> None:
    bad = verify_exchange_keys(
        exchange_id="kraken",
        scope="query",
        fetch_balance=lambda: {},
        method_name="create_order",
    )
    assert bad.ok is False
    ok = verify_exchange_keys(
        exchange_id="kraken",
        scope="query",
        fetch_balance=lambda: {"total": {"USD": 1}},
    )
    assert ok.ok is True
    assert ok.verified_at
    text = success_dialog_text(ok)
    assert "kraken" in text
    assert "go-live" in text.lower() or "Live orders" in text
