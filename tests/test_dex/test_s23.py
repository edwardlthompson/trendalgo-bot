"""S23 DEX dry-run swap tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.dex.control import DexVenueControlStore
from trendalgo.dex.nonce import NonceStore
from trendalgo.dex.router import (
    dry_run_dex_swap,
    list_dex_swap_chains,
    live_dex_swap,
    preview_dex_swap,
)
from trendalgo.dex.runner.dry_run import DexDryRunRunner
from trendalgo.venues.registry import get_swap_plugin, load_venue_registry


def test_registry_v3_swap_plugins() -> None:
    registry = load_venue_registry()
    assert registry.version == 4
    eth = get_swap_plugin("ethereum")
    assert eth.protocol == "uniswap_v3"
    jup = get_swap_plugin("solana")
    assert jup.protocol == "jupiter"
    assert set(list_dex_swap_chains()) == {"ethereum", "base", "arbitrum", "solana"}


def test_uniswap_v3_swap_preview_and_simulate() -> None:
    preview = preview_dex_swap("base", "ETH", "USDC", 0.5)
    assert preview["mode"] == "preview"
    assert preview["read_only"] is True
    assert preview["tx_broadcast"] is False
    assert preview["buy_amount"] > 0

    sim = dry_run_dex_swap("base", "ETH", "USDC", 0.5, app_dry_run=True)
    assert sim["mode"] == "simulated"
    assert sim["simulation_id"].startswith("dex-sim-")
    assert sim["tx_broadcast"] is False


def test_jupiter_swap_dry_run() -> None:
    preview = preview_dex_swap("solana", "SOL", "USDC", 2.0)
    assert preview["protocol"] == "jupiter"
    assert preview["chain"] == "solana"

    sim = dry_run_dex_swap("solana", "SOL", "USDC", 2.0, app_dry_run=True)
    assert sim["mode"] == "simulated"


def test_dex_trading_ack_gate(monkeypatch) -> None:
    monkeypatch.delenv("DEX_TRADING_ACK", raising=False)
    with pytest.raises(ValueError, match="DEX_TRADING_ACK"):
        dry_run_dex_swap("ethereum", "ETH", "USDC", 1.0, app_dry_run=False)
    monkeypatch.setenv("DEX_TRADING_ACK", "1")
    sim = dry_run_dex_swap("ethereum", "ETH", "USDC", 1.0, app_dry_run=False)
    assert sim["mode"] == "simulated"


def test_live_swap_blocked_without_gates(tmp_path: Path) -> None:
    control = DexVenueControlStore(tmp_path / "dex_control.db")
    nonce = NonceStore(tmp_path / "nonces.json")
    with pytest.raises(ValueError, match="H-036"):
        live_dex_swap(
            "base",
            "ETH",
            "USDC",
            1.0,
            control=control,
            nonce_store=nonce,
        )


def test_dex_dry_run_runner_history() -> None:
    runner = DexDryRunRunner(app_dry_run=True)
    preview = runner.preview("arbitrum", "ETH", "USDC", 1.0)
    assert preview["mode"] == "preview"
    executed = runner.execute("arbitrum", "ETH", "USDC", 1.0)
    assert executed["mode"] == "simulated"
    assert len(runner.history) == 1


def test_s23_api_routes() -> None:
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    client = TestClient(create_app())
    chains = client.get("/api/v1/platform/dex/swap-chains")
    assert chains.status_code == 200
    assert "ethereum" in chains.json()["chains"]

    preview = client.get(
        "/api/v1/platform/dex/preview",
        params={"chain": "ethereum", "sell_token": "ETH", "buy_token": "USDC", "sell_amount": 1},
    )
    assert preview.status_code == 200
    assert preview.json()["protocol"] == "uniswap_v3"

    dry = client.post(
        "/api/v1/platform/dex/dry-run",
        json={"chain": "solana", "sell_token": "SOL", "buy_token": "USDC", "sell_amount": 1.5},
    )
    assert dry.status_code == 200
    body = dry.json()
    assert body["protocol"] == "jupiter"
    assert body["simulation_id"]
