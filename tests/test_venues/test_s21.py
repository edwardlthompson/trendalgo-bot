"""S21 DEX venue plugin foundation tests."""

from __future__ import annotations

from pathlib import Path

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.onchain import preview_onchain_wallet, sync_onchain_wallet
from trendalgo.venues.registry import get_venue, list_wallet_venues, load_venue_registry
from trendalgo.venues.wallet_sync import preview_wallet

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
SOL_ADDR = "7EcDhSYGxXyscesiyR6Y3Gf4zEWLUsRms95TMPMXLKm"


def test_venue_registry_s21() -> None:
    registry = load_venue_registry()
    assert registry.version == 4
    ids = {v.id for v in list_wallet_venues()}
    assert ids == {"ethereum", "base", "arbitrum", "solana"}
    eth = get_venue("ethereum")
    assert eth.chain_type == "evm" and eth.chain_id == 1
    sol = get_venue("solana")
    assert sol.chain_type == "solana"


def test_evm_and_solana_dry_run_preview() -> None:
    for venue_id in ("ethereum", "base", "arbitrum"):
        result = preview_wallet(EVM_ADDR, venue_id=venue_id)
        assert result["venue"] == venue_id
        assert result["total_usd"] > 0
        assert result["read_only"] is True
    sol = preview_wallet(SOL_ADDR, venue_id="solana")
    assert sol["chain_type"] == "solana"
    assert sol["holdings"]


def test_onchain_delegates_to_plugins(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    preview = preview_onchain_wallet(EVM_ADDR, chain="base")
    assert preview["venue"] == "base"
    synced = sync_onchain_wallet(store, EVM_ADDR, chain="arbitrum", dry_run=True)
    assert synced["dry_run"] is True
    assert synced["registry_version"] == 4
    assert synced["holdings"]


def test_unsupported_chain_rejected() -> None:
    try:
        preview_onchain_wallet(EVM_ADDR, chain="polygon")
        raise AssertionError("expected unsupported chain")
    except ValueError as exc:
        assert "unsupported chain" in str(exc)


def test_venues_registry_api() -> None:
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/platform/venues/registry")
    body = resp.json()
    assert resp.status_code == 200
    assert body["version"] == 4
    assert len(body["venues"]) == 4
    sync = client.post(
        "/api/v1/platform/onchain/sync",
        json={"address": SOL_ADDR, "chain": "solana"},
    )
    assert sync.status_code == 200
    assert sync.json()["venue"] == "solana"
