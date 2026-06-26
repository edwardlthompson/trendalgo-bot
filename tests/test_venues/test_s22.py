"""S22 DEX portfolio plugin tests."""

from __future__ import annotations

from pathlib import Path

from trendalgo.billing.venue_attribution import attribution_by_venue
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.dex_positions import list_dex_positions_from_store, preview_dex_positions
from trendalgo.portfolio.onchain import sync_onchain_wallet
from trendalgo.venues.orchestrator import sync_all_wallet_venues
from trendalgo.venues.plugins.zero_ex import preview_quote
from trendalgo.venues.registry import get_lp_plugin, get_venue, load_venue_registry
from trendalgo.venues.wallet_sync import preview_wallet, sync_wallet

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
SOL_ADDR = "7EcDhSYGxXyscesiyR6Y3Gf4zEWLUsRms95TMPMXLKm"


def test_registry_v2_portfolio_plugins() -> None:
    registry = load_venue_registry()
    assert registry.version == 4
    eth = get_venue("ethereum")
    assert "uniswap_v3" in eth.portfolio_plugins
    sol = get_venue("solana")
    assert sol.portfolio_plugins == ()


def test_uniswap_v3_lp_dry_run() -> None:
    plugin = get_lp_plugin("ethereum")
    positions = plugin.read_lp_positions(EVM_ADDR, dry_run=True)
    assert len(positions) >= 2
    assert positions[0].protocol == "uniswap_v3"
    assert positions[0].liquidity_usd > 0


def test_wallet_preview_includes_lp() -> None:
    preview = preview_wallet(EVM_ADDR, venue_id="base", include_lp=True)
    assert preview["lp_total_usd"] > 0
    assert preview["lp_positions"]
    assert preview["total_usd"] == preview["wallet_total_usd"] + preview["lp_total_usd"]


def test_zero_ex_quote_dry_run() -> None:
    quote = preview_quote("ethereum", "ETH", "USDC", 1.0, dry_run=True)
    assert quote["read_only"] is True
    assert quote["source"] == "dry-run"
    assert quote["buy_amount"] > 0
    assert quote["chain"] == "ethereum"


def test_multi_chain_sync_and_attribution(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_VENUE_SYNC_STAGGER_SEC", "0")
    store = PortfolioStore(tmp_path / "portfolio.db")
    result = sync_all_wallet_venues(store, EVM_ADDR, dry_run=True, include_lp=True)
    assert result["staggered"] is True
    assert result["synced_count"] == 3
    assert result["venue_count"] == 4
    assert "solana" in result
    assert result["solana"].get("skipped") is True
    attr = result["attribution_by_venue"]
    assert attr["ethereum"] > 0
    assert attr["base"] > 0
    assert sum(attr.values()) > 0
    assert attribution_by_venue(result) == attr


def test_dex_positions_from_store(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    sync_wallet(store, EVM_ADDR, venue_id="ethereum", dry_run=True, include_lp=True)
    listed = list_dex_positions_from_store(store)
    assert listed["lp_total_usd"] > 0
    assert listed["lp_positions"]


def test_preview_dex_all_evm_chains() -> None:
    result = preview_dex_positions(EVM_ADDR)
    assert result["chain"] == "all-evm"
    assert len(result["lp_positions"]) >= 6


def test_s22_api_routes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_VENUE_SYNC_STAGGER_SEC", "0")
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    client = TestClient(create_app())
    quote = client.get(
        "/api/v1/platform/dex/quote",
        params={"chain": "arbitrum", "sell_token": "ETH", "buy_token": "USDC", "sell_amount": 0.5},
    )
    assert quote.status_code == 200
    assert quote.json()["chain"] == "arbitrum"

    preview = client.get(
        f"/api/v1/platform/onchain/preview/{EVM_ADDR}",
        params={"chain": "ethereum", "include_lp": "true"},
    )
    assert preview.status_code == 200
    assert preview.json()["lp_positions"]

    sync_all = client.post(
        "/api/v1/platform/onchain/sync-all",
        json={"address": EVM_ADDR, "include_lp": True},
    )
    assert sync_all.status_code == 200
    assert sync_all.json()["attribution_by_venue"]

    dex_pos = client.get(
        "/api/v1/portfolio/dex/positions",
        params={"address": EVM_ADDR, "chain": "base"},
    )
    assert dex_pos.status_code == 200
    assert dex_pos.json()["lp_positions"]


def test_onchain_sync_solana_with_lp_flag(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    synced = sync_onchain_wallet(store, SOL_ADDR, chain="solana", dry_run=True, include_lp=True)
    assert synced["lp_total_usd"] == 0
    assert synced["lp_positions"] == []
