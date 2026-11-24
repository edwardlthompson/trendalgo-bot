"""CredMan presence inventory — no secret blobs in payload."""

from __future__ import annotations

from trendalgo.device.alpaca_vault import ALPACA_KEY_TARGET, save_alpaca_creds
from trendalgo.device.credman_inventory import (
    ALGOSPECIAL_NOTE,
    frozen_targets,
    inventory_presence,
    inventory_summary,
)
from trendalgo.device.telegram_vault import TELEGRAM_TOKEN_TARGET, save_telegram_creds
from trendalgo.device.wizard.credentials import MemoryCredentialStore


def test_frozen_targets_include_core_namespaces() -> None:
    targets = {t for _, t in frozen_targets()}
    assert TELEGRAM_TOKEN_TARGET in targets
    assert ALPACA_KEY_TARGET in targets
    assert any(t.startswith("TrendAlgo/exchange/") for t in targets)
    assert "TrendAlgo/calendar-coinmarketcal" in targets
    assert "TrendAlgo/owner-secret" in targets


def test_inventory_presence_only_flags(memory_store: None = None) -> None:
    del memory_store
    store = MemoryCredentialStore()
    save_telegram_creds("tok", "123", store=store)
    save_alpaca_creds("PK", "SEC", store=store)
    rows = inventory_presence(store)
    by_target = {r["target"]: r for r in rows}
    assert by_target[TELEGRAM_TOKEN_TARGET]["present"] is True
    assert by_target[ALPACA_KEY_TARGET]["present"] is True
    for row in rows:
        assert set(row.keys()) <= {"kind", "target", "present", "error"}
        assert "123" not in str(row.values())
        assert "PK" not in str(row.values())
        assert "SEC" not in str(row.values())
        assert row["present"] is True or row["present"] is False


def test_inventory_summary_algospecial_note() -> None:
    store = MemoryCredentialStore()
    summary = inventory_summary(store)
    assert summary["secrets_exported"] is False
    assert summary["algospecial"] == ALGOSPECIAL_NOTE
    assert summary["total"] == len(summary["rows"])
